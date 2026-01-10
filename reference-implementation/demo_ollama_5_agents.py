from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

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
    scope: str = "text"


class ICNPAgent:
    def __init__(
        self,
        *,
        responder: Responder,
        action: str,
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

        self.capability = Capability(capability_id=new_uuid(), action=action, scope="text")

    def capability_message(self, intent_id: str) -> Dict[str, Any]:
        cap = {
            "id": self.capability.capability_id,
            "action": self.capability.action,
            "scope": self.capability.scope,
            "confidence": 0.8,
            "requires_approval": False,
            "side_effects": "none",
        }
        msg = make_capability_message(
            in_reply_to=intent_id,
            capabilities=[cap],
            responder=self.responder.to_dict(),
            resource_requirements={
                "compute": {"cpu_cores": 1, "memory_gb": 2},
                "estimated_duration_seconds": 120,
            },
        )
        ok, errors = self.schema.validate("capability.schema.json", msg)
        if not ok:
            raise ValueError(f"Capability message schema errors: {errors}")
        return msg

    def verify_and_execute(
        self,
        *,
        action: str,
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
        output_text = self.perform_action(action, parameters)
        ended_at = utc_now_iso()

        return {
            "agent_id": self.responder.id,
            "capability_id": self.capability.capability_id,
            "action": action,
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ollama-url", default="http://localhost:11434")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--model", default=None, help="Default model for all agents (unless overridden).")
    ap.add_argument("--model-planner", default=None)
    ap.add_argument("--model-writer", default=None)
    ap.add_argument("--model-reviewer", default=None)
    ap.add_argument("--model-summariser", default=None)
    args = ap.parse_args()

    base = Path(__file__).resolve().parent
    schema = SchemaRegistry(str((base.parent / "schemas").resolve()))

    secret = b"icnp-demo-secret"
    ollama = None if args.dry_run else OllamaClient(args.ollama_url)

    def choose_model(override: Optional[str]) -> str:
        return override or args.model or "llama3.1:8b"

    orchestrator = Sender(id="agent-orchestrator", type="autonomous-agent", trust_level="trusted")

    agents = [
        ICNPAgent(
            responder=Responder(id="agent-planner", version="1.0"),
            action="suggest",
            model=choose_model(args.model_planner),
            system_prompt="You are a planning agent. Produce clear bullet-point outlines.",
            secret=secret,
            dry_run=args.dry_run,
            schema=schema,
            ollama=ollama,
        ),
        ICNPAgent(
            responder=Responder(id="agent-writer", version="1.0"),
            action="transform",
            model=choose_model(args.model_writer),
            system_prompt="You are a technical writer. Write clear, accurate explanations for engineers.",
            secret=secret,
            dry_run=args.dry_run,
            schema=schema,
            ollama=ollama,
        ),
        ICNPAgent(
            responder=Responder(id="agent-reviewer", version="1.0"),
            action="analyze",
            model=choose_model(args.model_reviewer),
            system_prompt="You are a careful reviewer. Identify issues and suggest improvements.",
            secret=secret,
            dry_run=args.dry_run,
            schema=schema,
            ollama=ollama,
        ),
        ICNPAgent(
            responder=Responder(id="agent-summariser", version="1.0"),
            action="transform",
            model=choose_model(args.model_summariser),
            system_prompt="You are a summariser. Produce a concise final answer.",
            secret=secret,
            dry_run=args.dry_run,
            schema=schema,
            ollama=ollama,
        ),
    ]

    intent_goal = "Explain how Coloured Petri Nets (CPNs) relate to CTL/LTL model checking."
    intent = {
        "action": "explain-cpn-ctl-ltl",
        "goals": [
            {"id": "explain-topic", "priority": "critical", "description": intent_goal},
            {"id": "outline", "priority": "high", "description": "Outline the explanation"},
            {"id": "draft", "priority": "high", "description": "Draft the explanation"},
            {"id": "review", "priority": "medium", "description": "Review for clarity and accuracy"},
            {"id": "summary", "priority": "medium", "description": "Summarise into final text"},
        ],
        "non_goals": [
            {"id": "no-new-theory", "reason": "Avoid unrelated formalism", "severity": "soft"}
        ],
        "constraints": {
            "time_window": {"start": "09:00", "end": "18:00", "timezone": "UTC"},
            "resources": {"max_cpu_cores": 2, "max_memory_gb": 4},
        },
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

    contract_id = new_uuid()
    agreed_actions = [
        {"capability_id": ag.capability.capability_id, "approved": True, "max_invocations": 1}
        for ag in agents
    ]
    execution_constraints = {
        "audit_level": "standard",
        "logging_required": True,
        "rollback_required": False,
        "max_duration_seconds": 600,
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
    jprint("SEND -> CONTRACT_NEGOTIATION (orchestrator -> participants)", contract_obj)

    binding = make_binding_hashes(intent_msg["intent"], contract_obj, capability_records)

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
    jprint("SEND -> EXECUTION_TOKEN (issuer -> participants)", token_msg)

    token_meta = {"body": token_body, "signature": token_signature}

    goal_note = (
        f"Intent: {intent_goal}\n"
        "Note: CPNs means Coloured Petri Nets (not Constraint Programming Networks).\n\n"
    )
    prompts = {
        "agent-planner": "Create a structured outline. Use 5-8 bullet points.",
        "agent-writer": "Write a ~250 word draft. Clear, technical, no fluff.",
        "agent-reviewer": "Review the following text and suggest improvements (accuracy, clarity, structure). Provide bullet points.",
        "agent-summariser": "Summarise the final content into a concise 120-160 word explanation.",
    }

    outputs: Dict[str, str] = {}

    for ag in agents:
        prompt = prompts[ag.responder.id]
        if ag.responder.id == "agent-writer":
            prompt += "\n\nOUTLINE:\n" + outputs.get("agent-planner", "[outline missing]")
        if ag.responder.id == "agent-reviewer":
            prompt += "\n\nDRAFT:\n" + outputs.get("agent-writer", "[draft missing]")
        if ag.responder.id == "agent-summariser":
            prompt += "\n\nDRAFT:\n" + outputs.get("agent-writer", "") + "\n\nREVIEW:\n" + outputs.get("agent-reviewer", "")

        params = {"prompt": goal_note + prompt}
        result = ag.verify_and_execute(
            action=ag.capability.action,
            parameters=params,
            token_meta=token_meta,
            contract_obj=contract_obj,
        )
        jprint(f"EXECUTION_RESULT ({ag.responder.id})", result)
        if result.get("status") == "success":
            outputs[ag.responder.id] = result["output"]["text"]

    print("\n" + "#" * 90)
    print("FINAL ARTEFACTS")
    print("#" * 90)
    print(f"\n--- outline ---\n{outputs.get('agent-planner', '')}")
    print(f"\n--- draft ---\n{outputs.get('agent-writer', '')}")
    print(f"\n--- review ---\n{outputs.get('agent-reviewer', '')}")
    print(f"\n--- summary ---\n{outputs.get('agent-summariser', '')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
