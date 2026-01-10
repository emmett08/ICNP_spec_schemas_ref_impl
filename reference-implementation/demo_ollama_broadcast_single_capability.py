from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from icnp.runtime import (
    Actor,
    SchemaRegistry,
    make_binding_hashes,
    make_envelope,
    new_uuid,
    rand_nonce,
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
        actor: Actor,
        model: str,
        system_prompt: str,
        secret: bytes,
        dry_run: bool,
        schema: SchemaRegistry,
        ollama: Optional[OllamaClient] = None,
    ):
        self.actor = actor
        self.model = model
        self.system_prompt = system_prompt
        self.secret = secret
        self.dry_run = dry_run
        self.schema = schema
        self.ollama = ollama
        self.invocations_by_token: Dict[str, int] = {}

        # Each agent advertises exactly one capability in this demo.
        self.capability = Capability(capability_id=new_uuid(), action="")

    def capability_message(self, session_id: str, in_reply_to: str, recipient: Actor, action: str) -> Dict[str, Any]:
        self.capability.action = action
        msg = make_envelope(
            icnp_version="1.0.0",
            msg_type="capability_disclosure",
            phase="capability",
            sender=self.actor,
            recipient=recipient,
            session_id=session_id,
            in_reply_to=in_reply_to,
            payload={
                "capabilities": [
                    {
                        "capability_id": self.capability.capability_id,
                        "name": f"{self.actor.display_name} capability",
                        "description": f"{self.actor.display_name} can perform {action}.",
                        "actions": [
                            {
                                "action": action,
                                "scopes": ["text"],
                                "requires_approval": False,
                                "confidence": 0.8,
                                "effects": "none",
                            }
                        ],
                    }
                ]
            },
        )
        ok, errors = self.schema.validate("capability.schema.json", msg)
        if not ok:
            raise ValueError(f"Capability message schema errors: {errors}")
        return msg

    def accept_contract(self, session_id: str, in_reply_to: str, recipient: Actor, contract_obj: Dict[str, Any]) -> Dict[str, Any]:
        msg = make_envelope(
            icnp_version="1.0.0",
            msg_type="contract_acceptance",
            phase="contract",
            sender=self.actor,
            recipient=recipient,
            session_id=session_id,
            in_reply_to=in_reply_to,
            payload={"contract": contract_obj, "decision": "accept"},
        )
        ok, errors = self.schema.validate("contract.schema.json", msg)
        if not ok:
            raise ValueError(f"Contract acceptance schema errors: {errors}")
        return msg

    def verify_and_execute(self, message: Dict[str, Any], token_msg: Dict[str, Any], contract_obj: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Handle an execution_request and return [execution_result, audit_event].
        """
        request = message["payload"]["request"]
        token = token_msg["payload"]["token"]

        # Basic token checks: signature + time + audience + per-actor invocations.
        token_body = dict(token)
        signature = token_body.pop("signature")
        if not verify_token_hmac(token_body, signature, secret=self.secret):
            return [self.error_msg(message, "ICNP-005", "Token signature invalid")]

        now = datetime.now(timezone.utc)
        nb = datetime.fromisoformat(token["not_before"].replace("Z", "+00:00"))
        na = datetime.fromisoformat(token["not_after"].replace("Z", "+00:00"))
        if not (nb <= now < na):
            return [self.error_msg(message, "ICNP-005", "Token expired or not yet valid")]

        allowed_audience = {a["id"] for a in token["audience"]}
        if self.actor.id not in allowed_audience:
            return [self.error_msg(message, "ICNP-004", "Actor not in token audience")]

        # Per-actor limit enforcement
        tok_id = token["token_id"]
        self.invocations_by_token.setdefault(tok_id, 0)
        self.invocations_by_token[tok_id] += 1
        if self.invocations_by_token[tok_id] > token["limits"]["max_invocations_per_actor"]:
            return [self.error_msg(message, "ICNP-004", "Invocation limit exceeded")]

        # Contract check: action permitted for this executor
        action = request["action"]
        permitted = False
        for aa in contract_obj["agreed_actions"]:
            if aa["executor_id"] == self.actor.id and aa["action"] == action:
                permitted = True
                break
        if not permitted:
            return [self.error_msg(message, "ICNP-004", f"Action '{action}' not permitted for {self.actor.id}")]

        started_at = utc_now_iso()
        output_text = self.perform_action(action, request.get("parameters", {}))
        ended_at = utc_now_iso()

        result_env = make_envelope(
            icnp_version="1.0.0",
            msg_type="execution_result",
            phase="execution",
            sender=self.actor,
            recipient=Actor(
                id=message["sender"]["id"],
                role=message["sender"]["role"],
                display_name=message["sender"].get("display_name"),
            ),
            session_id=message["session_id"],
            in_reply_to=message["message_id"],
            payload={
                "result": {
                    "invocation_id": request["invocation_id"],
                    "token_id": request["token_id"],
                    "contract_id": request["contract_id"],
                    "status": "success",
                    "started_at": started_at,
                    "ended_at": ended_at,
                    "output": {"text": output_text},
                }
            },
        )
        ok, errors = self.schema.validate("execution.schema.json", result_env)
        if not ok:
            raise ValueError(f"Execution result schema errors: {errors}")

        audit_env = make_envelope(
            icnp_version="1.0.0",
            msg_type="audit_event",
            phase="audit",
            sender=self.actor,
            session_id=message["session_id"],
            payload={
                "event": {
                    "event_id": new_uuid(),
                    "session_id": message["session_id"],
                    "related_message_id": message["message_id"],
                    "invocation_id": request["invocation_id"],
                    "event_type": "execution_completed",
                    "actor": self.actor.__dict__ | {"display_name": self.actor.display_name},
                    "timestamp": utc_now_iso(),
                    "severity": "info",
                    "details": {"action": action, "status": "success"},
                }
            },
        )
        ok, errors = self.schema.validate("audit.schema.json", audit_env)
        if not ok:
            raise ValueError(f"Audit schema errors: {errors}")

        return [result_env, audit_env]

    def perform_action(self, action: str, parameters: Dict[str, Any]) -> str:
        if self.dry_run or self.ollama is None:
            return f"[dry-run:{self.actor.id}] Completed {action} with parameters={parameters!r}"

        user_prompt = parameters.get("prompt", f"Perform action: {action}. Parameters: {json.dumps(parameters)}")
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return self.ollama.chat(self.model, messages)

    def error_msg(self, related_message: Dict[str, Any], code: str, message: str) -> Dict[str, Any]:
        env = make_envelope(
            icnp_version="1.0.0",
            msg_type="error",
            phase="error",
            sender=self.actor,
            recipient=Actor(
                id=related_message["sender"]["id"],
                role=related_message["sender"]["role"],
                display_name=related_message["sender"].get("display_name"),
            ),
            session_id=related_message["session_id"],
            in_reply_to=related_message["message_id"],
            payload={
                "error": {
                    "error_id": new_uuid(),
                    "code": code,
                    "message": message,
                    "retryable": False,
                    "related_message_id": related_message["message_id"],
                    "timestamp": utc_now_iso(),
                }
            },
        )
        ok, errors = self.schema.validate("error.schema.json", env)
        if not ok:
            raise ValueError(f"Error schema errors: {errors}")
        return env


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ollama-url", default="http://localhost:11434")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--model", default=None, help="Default model for all agents.")
    args = ap.parse_args()

    base = Path(__file__).resolve().parent
    schema = SchemaRegistry(str((base.parent / "schemas").resolve()))

    # Shared demo secret for HMAC signing (all agents share in this demo).
    secret = b"icnp-demo-secret"

    ollama = None if args.dry_run else OllamaClient(args.ollama_url)

    def choose_model(override: Optional[str]) -> str:
        return override or args.model or "llama3.1:8b"

    orchestrator = Actor(id="agent-orchestrator", role="orchestrator", display_name="Orchestrator")

    agent_profiles = [
        ("agent-planner", "Planner", "compose_outline", "You are a planning agent. Produce clear bullet-point outlines."),
        ("agent-writer", "Writer", "write_draft", "You are a technical writer. Write clear, accurate explanations for engineers."),
        ("agent-reviewer", "Reviewer", "review_text", "You are a careful reviewer. Identify issues and suggest improvements."),
        ("agent-summariser", "Summariser", "summarise_text", "You are a summariser. Produce concise answers."),
        ("agent-classifier", "Classifier", "classify_tone", "You classify tone and sentiment with short labels."),
        ("agent-analyst", "Analyst", "analyze_data", "You analyze data and return key patterns."),
        ("agent-ranker", "Ranker", "rank_options", "You rank options by criteria and explain the ranking."),
        ("agent-translator", "Translator", "translate_text", "You translate text between languages."),
        ("agent-validator", "Validator", "validate_output", "You validate outputs against requirements."),
    ]

    agents = [
        ICNPAgent(
            actor=Actor(id=aid, role="agent", display_name=name),
            model=choose_model(None),
            system_prompt=prompt,
            secret=secret,
            dry_run=args.dry_run,
            schema=schema,
            ollama=ollama,
        )
        for aid, name, _action, prompt in agent_profiles
    ]

    action_by_agent = {aid: action for aid, _name, action, _prompt in agent_profiles}

    session_id = new_uuid()

    requested_action = "translate_text"
    intent_goal = "Translate the provided text from English to Spanish."
    source_text = (
        "The verification team will review the model tomorrow. "
        "Please prepare a short summary of the key assumptions."
    )

    # ---------------- Phase 1: Intent ----------------
    intent = make_envelope(
        icnp_version="1.0.0",
        msg_type="intent_declaration",
        phase="intent",
        sender=orchestrator,
        session_id=session_id,
        payload={
            "intent": {
                "goal": intent_goal,
                "requested_actions": [
                    {"action": requested_action, "description": "Translate the provided text to Spanish."}
                ],
                "expected_outputs": ["translation"],
            },
            "constraints": {
                "risk_tolerance": "low",
                "human_approval_required": False,
                "external_side_effects_allowed": False,
                "audit_level": "standard",
                "data_policy": {"allowed_data_classes": ["public"], "retention_days": 0},
            },
        },
    )
    ok, errors = schema.validate("intent.schema.json", intent)
    if not ok:
        raise ValueError(f"Intent schema errors: {errors}")
    jprint("SEND -> INTENT_DECLARATION (orchestrator -> broadcast)", intent)

    # ---------------- Phase 2: Capability disclosures ----------------
    cap_msgs: List[Dict[str, Any]] = []
    for ag in agents:
        cap = ag.capability_message(session_id, intent["message_id"], orchestrator, action_by_agent[ag.actor.id])
        cap_msgs.append(cap)
        jprint(f"RECV <- CAPABILITY_DISCLOSURE ({ag.actor.id} -> orchestrator)", cap)

    capabilities_payload = {"capabilities": []}
    for cap_msg in cap_msgs:
        capabilities_payload["capabilities"].extend(cap_msg["payload"]["capabilities"])

    matching_agents = [ag for ag in agents if ag.capability.action == requested_action]
    if len(matching_agents) != 1:
        raise ValueError(
            f"Expected exactly one agent with capability '{requested_action}', "
            f"found {len(matching_agents)}."
        )
    selected_agent = matching_agents[0]

    print("\n" + "#" * 90)
    print("CAPABILITY MATCH")
    print("#" * 90)
    print(f"Selected agent: {selected_agent.actor.id} ({selected_agent.actor.display_name})")

    # ---------------- Phase 3: Contract proposal + acceptance ----------------
    contract_id = new_uuid()
    issued_at = utc_now_iso()

    agreed_actions = [
        {
            "action_id": new_uuid(),
            "capability_id": selected_agent.capability.capability_id,
            "executor_id": selected_agent.actor.id,
            "action": selected_agent.capability.action,
            "scope": "text",
            "max_invocations": 1,
        }
    ]

    contract_obj = {
        "contract_id": contract_id,
        "session_id": session_id,
        "issued_at": issued_at,
        "parties": [orchestrator.to_dict(), selected_agent.actor.to_dict()],
        "agreed_actions": agreed_actions,
        "forbidden_actions": [{"action": "network_access", "reason": "No external side-effects allowed"}],
        "constraints": {"risk_tolerance": "low"},
        "enforcement": {
            "mode": "strict",
            "violation_action": "abort",
            "audit_level": "standard",
            "logging_required": True,
            "rollback_required": False,
        },
        "approvals": [],
        "signatures": [],
    }

    contract_proposal = make_envelope(
        icnp_version="1.0.0",
        msg_type="contract_proposal",
        phase="contract",
        sender=orchestrator,
        recipient=selected_agent.actor,
        session_id=session_id,
        payload={"contract": contract_obj},
    )
    ok, errors = schema.validate("contract.schema.json", contract_proposal)
    if not ok:
        raise ValueError(f"Contract proposal schema errors: {errors}")
    jprint("SEND -> CONTRACT_PROPOSAL (orchestrator -> translator)", contract_proposal)

    acc = selected_agent.accept_contract(session_id, contract_proposal["message_id"], orchestrator, contract_obj)
    jprint(f"RECV <- CONTRACT_ACCEPTANCE ({selected_agent.actor.id} -> orchestrator)", acc)

    # ---------------- Phase 4: Token issuance ----------------
    intent_payload = intent["payload"]
    binding = make_binding_hashes(intent_payload, contract_obj, capabilities_payload)

    not_before = datetime.now(timezone.utc).replace(microsecond=0)
    not_after = not_before + timedelta(minutes=10)

    token_body = {
        "token_id": new_uuid(),
        "session_id": session_id,
        "contract_id": contract_id,
        "issuer": orchestrator.to_dict(),
        "audience": [selected_agent.actor.to_dict()],
        "issued_at": utc_now_iso(),
        "not_before": not_before.isoformat().replace("+00:00", "Z"),
        "not_after": not_after.isoformat().replace("+00:00", "Z"),
        "limits": {"max_invocations_per_actor": 1, "max_invocations_total": 1},
        "binding": binding,
        "revocation": {"method": "out_of_band"},
    }
    signature = sign_token_hmac(token_body, secret=secret, signed_by=orchestrator.id)
    token = dict(token_body)
    token["signature"] = signature

    token_msg = make_envelope(
        icnp_version="1.0.0",
        msg_type="execution_token",
        phase="token",
        sender=orchestrator,
        recipient=selected_agent.actor,
        session_id=session_id,
        payload={"token": token},
    )
    ok, errors = schema.validate("execution-token.schema.json", token_msg)
    if not ok:
        raise ValueError(f"Token schema errors: {errors}")
    jprint("SEND -> EXECUTION_TOKEN (orchestrator -> translator)", token_msg)

    # ---------------- Governed execution ----------------
    intent_goal_note = f"Goal: {intent_goal}\n\n"
    prompt = (
        intent_goal_note
        + "Translate the following text to Spanish. Keep the meaning and tone.\n\nTEXT:\n"
        + source_text
    )
    params = {
        "prompt": prompt,
        "source_text": source_text,
        "target_language": "Spanish",
    }

    req = make_envelope(
        icnp_version="1.0.0",
        msg_type="execution_request",
        phase="execution",
        sender=orchestrator,
        recipient=selected_agent.actor,
        session_id=session_id,
        payload={
            "request": {
                "invocation_id": new_uuid(),
                "token_id": token["token_id"],
                "contract_id": contract_id,
                "action": requested_action,
                "executor": selected_agent.actor.to_dict(),
                "requested_at": utc_now_iso(),
                "nonce": rand_nonce(),
                "parameters": params,
            }
        },
    )
    ok, errors = schema.validate("execution.schema.json", req)
    if not ok:
        raise ValueError(f"Execution request schema errors: {errors}")
    jprint(f"SEND -> EXECUTION_REQUEST ({orchestrator.id} -> {selected_agent.actor.id})", req)

    responses = selected_agent.verify_and_execute(req, token_msg, contract_obj)
    for resp in responses:
        if resp["type"] == "execution_result":
            jprint(f"RECV <- EXECUTION_RESULT ({selected_agent.actor.id} -> orchestrator)", resp)
        elif resp["type"] == "audit_event":
            jprint(f"AUDIT <- AUDIT_EVENT ({selected_agent.actor.id})", resp)
        else:
            jprint(f"RECV <- {resp['type']} ({selected_agent.actor.id} -> orchestrator)", resp)

    print("\n" + "#" * 90)
    print("FINAL OUTPUT")
    print("#" * 90)
    for resp in responses:
        if resp["type"] == "execution_result":
            print(resp["payload"]["result"]["output"].get("text", ""))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
