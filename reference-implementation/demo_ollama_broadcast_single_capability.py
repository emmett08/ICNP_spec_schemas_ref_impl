from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from icnp.runtime import (
    Responder,
    SchemaRegistry,
    Sender,
    make_binding_hashes,
    make_capability_message,
    make_contract_message,
    make_demo_token,
    make_execution_token_message,
    make_intent_message,
    new_uuid,
    sign_token_hmac,
    utc_now_iso,
    verify_token_hmac,
)
from icnp.ollama import OllamaClient


def jprint(title: str, msg: Dict[str, Any]) -> None:
    print("\n" + "=" * 90)
    print(title)
    print("-" * 90)
    print(json.dumps(msg, indent=2, ensure_ascii=False))
    print("=" * 90 + "\n")


@dataclass
class Capability:
    capability_id: str
    action: str
    scope: str


@dataclass
class AgentProfile:
    agent_id: str
    name: str
    action: str
    scope: str
    system_prompt: str


class ICNPAgent:
    def __init__(
        self,
        *,
        responder: Responder,
        action: str,
        scope: str,
        model: str,
        system_prompt: str,
        secret: bytes,
        dry_run: bool,
        schema: SchemaRegistry,
        ollama: Optional[OllamaClient] = None,
    ):
        self.responder = responder
        self.system_prompt = system_prompt
        self.model = model
        self.secret = secret
        self.dry_run = dry_run
        self.schema = schema
        self.ollama = ollama
        self.invocations_by_token: Dict[str, int] = {}

        self.capability = Capability(capability_id=new_uuid(), action=action, scope=scope)

    def capability_message(self, intent_id: str) -> Dict[str, Any]:
        cap = {
            "id": self.capability.capability_id,
            "action": self.capability.action,
            "scope": self.capability.scope,
            "confidence": 0.85,
            "requires_approval": False,
            "side_effects": "none",
        }
        msg = make_capability_message(
            in_reply_to=intent_id,
            capabilities=[cap],
            responder=self.responder.to_dict(),
        )
        ok, errors = self.schema.validate("capability.schema.json", msg)
        if not ok:
            raise ValueError(f"Capability message schema errors: {errors}")
        return msg

    def verify_and_execute(
        self,
        *,
        parameters: Dict[str, Any],
        token_meta: Dict[str, Any],
        contract_obj: Dict[str, Any],
    ) -> Dict[str, Any]:
        token_body = token_meta["body"]
        signature = token_meta["signature"]
        if not verify_token_hmac(token_body, signature, secret=self.secret):
            return self.execution_error("Token signature invalid")

        validity = token_body["validity"]
        now = datetime.now(timezone.utc)
        nb = datetime.fromisoformat(validity["not_before"].replace("Z", "+00:00"))
        na = datetime.fromisoformat(validity["not_after"].replace("Z", "+00:00"))
        if not (nb <= now < na):
            return self.execution_error("Token expired or not yet valid")

        token_id = token_body["token_id"]
        max_invocations = validity.get("max_invocations", 1)
        self.invocations_by_token.setdefault(token_id, 0)
        self.invocations_by_token[token_id] += 1
        if self.invocations_by_token[token_id] > max_invocations:
            return self.execution_error("Invocation limit exceeded")

        permitted = any(
            aa["capability_id"] == self.capability.capability_id and aa.get("approved") is True
            for aa in contract_obj["agreed_actions"]
        )
        if not permitted:
            return self.execution_error("Capability not approved in contract")

        started_at = utc_now_iso()
        output_text = self.perform_action(self.capability.action, parameters)
        ended_at = utc_now_iso()

        return {
            "agent_id": self.responder.id,
            "capability_id": self.capability.capability_id,
            "action": self.capability.action,
            "status": "success",
            "started_at": started_at,
            "ended_at": ended_at,
            "output": {"text": output_text},
        }

    def execution_error(self, message: str) -> Dict[str, Any]:
        return {"agent_id": self.responder.id, "status": "denied", "error": message}

    def perform_action(self, action: str, parameters: Dict[str, Any]) -> str:
        if self.dry_run or self.ollama is None:
            return f"[dry-run:{self.responder.id}] Completed {action} with parameters={parameters!r}"

        user_prompt = parameters.get("prompt", f"Perform action: {action}. Parameters: {json.dumps(parameters)}")
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return self.ollama.chat(self.model, messages)


def match_capability(
    agents: List[ICNPAgent],
    *,
    required_action: str,
    required_scope: str,
) -> Tuple[List[ICNPAgent], List[ICNPAgent]]:
    matches = [
        ag
        for ag in agents
        if ag.capability.action == required_action and ag.capability.scope == required_scope
    ]
    non_matches = [ag for ag in agents if ag not in matches]
    return matches, non_matches


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ollama-url", default="http://localhost:11434")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--model", default=None, help="Default model for all agents.")
    args = ap.parse_args()

    base = Path(__file__).resolve().parent
    schema = SchemaRegistry(str((base.parent / "schemas").resolve()))

    secret = b"icnp-demo-secret"
    ollama = None if args.dry_run else OllamaClient(args.ollama_url)

    def choose_model(override: Optional[str]) -> str:
        return override or args.model or "llama3.1:8b"

    orchestrator = Sender(id="agent-orchestrator", type="autonomous-agent", trust_level="trusted")

    profiles = [
        AgentProfile("agent-planner", "Planner", "suggest", "documentation", "You are a planning agent."),
        AgentProfile("agent-writer", "Writer", "suggest", "documentation", "You are a technical writer."),
        AgentProfile("agent-reviewer", "Reviewer", "analyze", "documentation", "You are a careful reviewer."),
        AgentProfile("agent-summariser", "Summariser", "analyze", "documentation", "You summarise content."),
        AgentProfile("agent-classifier", "Classifier", "analyze", "text", "You classify tone and sentiment."),
        AgentProfile("agent-analyst", "Analyst", "analyze", "data", "You analyze data and extract patterns."),
        AgentProfile("agent-ranker", "Ranker", "decide", "options", "You rank options by criteria."),
        AgentProfile("agent-translator", "Translator", "transform", "text", "You translate text between languages."),
        AgentProfile("agent-validator", "Validator", "audit", "output", "You validate outputs against requirements."),
    ]

    agents = [
        ICNPAgent(
            responder=Responder(id=profile.agent_id, version="1.0"),
            action=profile.action,
            scope=profile.scope,
            model=choose_model(None),
            system_prompt=profile.system_prompt,
            secret=secret,
            dry_run=args.dry_run,
            schema=schema,
            ollama=ollama,
        )
        for profile in profiles
    ]

    intent = {
        "action": "translate-text",
        "goals": [
            {"id": "translate", "priority": "high", "description": "Translate the text to Spanish."}
        ],
        "non_goals": [{"id": "no-summarise", "reason": "Preserve full meaning", "severity": "hard"}],
        "constraints": {"time_window": {"start": "09:00", "end": "18:00", "timezone": "UTC"}},
        "risk_tolerance": "low",
        "human_approval_required": False,
        "context": {"environment": "development", "urgency": "soon"},
    }

    intent_msg = make_intent_message(intent=intent, sender=orchestrator.to_dict())
    ok, errors = schema.validate("intent.schema.json", intent_msg)
    if not ok:
        raise ValueError(f"Intent schema errors: {errors}")
    jprint("SEND -> INTENT_DECLARATION (orchestrator -> broadcast)", intent_msg)

    cap_msgs: List[Dict[str, Any]] = []
    capability_records: List[Dict[str, Any]] = []
    for ag in agents:
        cap_msg = ag.capability_message(intent_msg["message_id"])
        cap_msgs.append(cap_msg)
        capability_records.extend(cap_msg["capabilities"])
        jprint(f"RECV <- CAPABILITY_DISCLOSURE ({ag.responder.id} -> orchestrator)", cap_msg)

    required_action = "transform"
    required_scope = "text"
    matches, _ = match_capability(agents, required_action=required_action, required_scope=required_scope)
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one agent matching action '{required_action}' and scope '{required_scope}', "
            f"found {len(matches)}."
        )
    selected_agent = matches[0]

    print("\n" + "#" * 90)
    print("CAPABILITY MATCH")
    print("#" * 90)
    print(f"Selected agent: {selected_agent.responder.id}")

    contract_id = new_uuid()
    agreed_actions = [
        {
            "capability_id": selected_agent.capability.capability_id,
            "approved": True,
            "max_invocations": 1,
        }
    ]
    execution_constraints = {
        "audit_level": "standard",
        "logging_required": True,
        "rollback_required": False,
        "max_duration_seconds": 300,
    }
    forbidden_actions = [
        {"action": "execute", "scope": "network", "reason": "No external side-effects allowed"},
        {"action": "delete", "scope": "any", "reason": "Safety"},
    ]

    contract_obj = make_contract_message(
        contract_id=contract_id,
        agreed_actions=agreed_actions,
        execution_constraints=execution_constraints,
        forbidden_actions=forbidden_actions,
        signatures={"initiator": "demo-signature", "responder": "demo-signature"},
    )
    ok, errors = schema.validate("contract.schema.json", contract_obj)
    if not ok:
        raise ValueError(f"Contract schema errors: {errors}")
    jprint("SEND -> CONTRACT_NEGOTIATION (orchestrator -> translator)", contract_obj)

    agreed_capabilities = [
        cap for cap in capability_records if cap["id"] == selected_agent.capability.capability_id
    ]
    binding = make_binding_hashes(intent_msg["intent"], contract_obj, agreed_capabilities)

    not_before = datetime.now(timezone.utc).replace(microsecond=0)
    not_after = not_before + timedelta(minutes=10)
    validity = {
        "not_before": not_before.isoformat().replace("+00:00", "Z"),
        "not_after": not_after.isoformat().replace("+00:00", "Z"),
        "max_invocations": 1,
    }
    enforcement = {"mode": "strict", "violation_action": "abort_and_rollback", "alert_on_violation": True}

    token_id = new_uuid()
    token_body = {
        "token_id": token_id,
        "contract_id": contract_id,
        "validity": validity,
        "binding": binding,
        "enforcement": enforcement,
    }
    token_signature = sign_token_hmac(token_body, secret=secret)
    token = make_demo_token(token_body, secret=secret)
    token_msg = make_execution_token_message(
        token_id=token_id,
        contract_id=contract_id,
        token=token,
        validity=validity,
        binding=binding,
        enforcement=enforcement,
    )
    ok, errors = schema.validate("execution-token.schema.json", token_msg)
    if not ok:
        raise ValueError(f"Token schema errors: {errors}")
    jprint("SEND -> EXECUTION_TOKEN (issuer -> translator)", token_msg)

    token_meta = {"body": token_body, "signature": token_signature}

    source_text = (
        "The verification team will review the model tomorrow. "
        "Please prepare a short summary of the key assumptions."
    )
    prompt = (
        "Translate the following text to Spanish. Keep the meaning and tone.\n\nTEXT:\n"
        + source_text
    )
    params = {"prompt": prompt, "source_text": source_text, "target_language": "Spanish"}

    result = selected_agent.verify_and_execute(
        parameters=params,
        token_meta=token_meta,
        contract_obj=contract_obj,
    )
    jprint(f"EXECUTION_RESULT ({selected_agent.responder.id})", result)

    print("\n" + "#" * 90)
    print("FINAL OUTPUT")
    print("#" * 90)
    if result.get("status") == "success":
        print(result["output"].get("text", ""))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
