\
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from icnp.runtime import (
    Actor, SchemaRegistry, make_binding_hashes, make_envelope, new_uuid, rand_nonce,
    sign_token_hmac, utc_now_iso, verify_token_hmac
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
                            {"action": action, "scopes": ["text"], "requires_approval": False, "confidence": 0.8, "effects": "none"}
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
            recipient=Actor(id=message["sender"]["id"], role=message["sender"]["role"], display_name=message["sender"].get("display_name")),
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
            recipient=Actor(id=related_message["sender"]["id"], role=related_message["sender"]["role"], display_name=related_message["sender"].get("display_name")),
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
    ap.add_argument("--model", default=None, help="Default model for all agents (unless overridden).")
    ap.add_argument("--model-orchestrator", default=None)
    ap.add_argument("--model-planner", default=None)
    ap.add_argument("--model-writer", default=None)
    ap.add_argument("--model-reviewer", default=None)
    ap.add_argument("--model-summariser", default=None)
    args = ap.parse_args()

    base = Path(__file__).resolve().parent
    schema = SchemaRegistry(str((base.parent / "schemas").resolve()))

    # Shared demo secret for HMAC signing (all agents share in this demo).
    secret = b"icnp-demo-secret"

    ollama = None if args.dry_run else OllamaClient(args.ollama_url)

    def choose_model(override: Optional[str]) -> str:
        return override or args.model or "llama3.1:8b"

    orchestrator = Actor(id="agent-orchestrator", role="orchestrator", display_name="Orchestrator")
    agents = [
        ICNPAgent(actor=Actor(id="agent-planner", role="agent", display_name="Planner"),
                 model=choose_model(args.model_planner), system_prompt="You are a planning agent. Produce clear bullet-point outlines.",
                 secret=secret, dry_run=args.dry_run, schema=schema, ollama=ollama),
        ICNPAgent(actor=Actor(id="agent-writer", role="agent", display_name="Writer"),
                 model=choose_model(args.model_writer), system_prompt="You are a technical writer. Write clear, accurate explanations for engineers.",
                 secret=secret, dry_run=args.dry_run, schema=schema, ollama=ollama),
        ICNPAgent(actor=Actor(id="agent-reviewer", role="agent", display_name="Reviewer"),
                 model=choose_model(args.model_reviewer), system_prompt="You are a careful reviewer. Identify issues and suggest improvements.",
                 secret=secret, dry_run=args.dry_run, schema=schema, ollama=ollama),
        ICNPAgent(actor=Actor(id="agent-summariser", role="agent", display_name="Summariser"),
                 model=choose_model(args.model_summariser), system_prompt="You are a summariser. Produce a concise final answer.",
                 secret=secret, dry_run=args.dry_run, schema=schema, ollama=ollama),
    ]

    session_id = new_uuid()

    # ---------------- Phase 1: Intent ----------------
    intent = make_envelope(
        icnp_version="1.0.0",
        msg_type="intent_declaration",
        phase="intent",
        sender=orchestrator,
        session_id=session_id,
        payload={
            "intent": {
                "goal": "Explain how Coloured Petri Nets relate to CTL/LTL model checking.",
                "requested_actions": [
                    {"action": "compose_outline", "description": "Outline the explanation"},
                    {"action": "write_draft", "description": "Draft the explanation"},
                    {"action": "review_text", "description": "Review and propose improvements"},
                    {"action": "summarise_text", "description": "Summarise into final text"},
                ],
                "expected_outputs": ["outline", "draft", "review_notes", "final_summary"],
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
    jprint("SEND → INTENT_DECLARATION (orchestrator → broadcast)", intent)

    # ---------------- Phase 2: Capability disclosures ----------------
    cap_msgs: List[Dict[str, Any]] = []
    action_by_agent = {
        "agent-planner": "compose_outline",
        "agent-writer": "write_draft",
        "agent-reviewer": "review_text",
        "agent-summariser": "summarise_text",
    }
    for ag in agents:
        cap = ag.capability_message(session_id, intent["message_id"], orchestrator, action_by_agent[ag.actor.id])
        cap_msgs.append(cap)
        jprint(f"RECV ← CAPABILITY_DISCLOSURE ({ag.actor.id} → orchestrator)", cap)

    # Build capabilities payload for binding hash
    capabilities_payload = {"capabilities": []}
    for cap_msg in cap_msgs:
        capabilities_payload["capabilities"].extend(cap_msg["payload"]["capabilities"])

    # ---------------- Phase 3: Contract proposal + acceptances ----------------
    contract_id = new_uuid()
    issued_at = utc_now_iso()

    agreed_actions = []
    for ag in agents:
        agreed_actions.append({
            "action_id": new_uuid(),
            "capability_id": ag.capability.capability_id,
            "executor_id": ag.actor.id,
            "action": ag.capability.action,
            "scope": "text",
            "max_invocations": 1
        })

    contract_obj = {
        "contract_id": contract_id,
        "session_id": session_id,
        "issued_at": issued_at,
        "parties": [orchestrator.to_dict()] + [a.actor.to_dict() for a in agents],
        "agreed_actions": agreed_actions,
        "forbidden_actions": [{"action": "network_access", "reason": "No external side-effects allowed"}],
        "constraints": {"risk_tolerance": "low"},
        "enforcement": {"mode": "strict", "violation_action": "abort", "audit_level": "standard", "logging_required": True, "rollback_required": False},
        "approvals": [],
        "signatures": [],
    }

    contract_proposal = make_envelope(
        icnp_version="1.0.0",
        msg_type="contract_proposal",
        phase="contract",
        sender=orchestrator,
        session_id=session_id,
        payload={"contract": contract_obj},
    )
    ok, errors = schema.validate("contract.schema.json", contract_proposal)
    if not ok:
        raise ValueError(f"Contract proposal schema errors: {errors}")
    jprint("SEND → CONTRACT_PROPOSAL (orchestrator → broadcast)", contract_proposal)

    accept_msgs = []
    for ag in agents:
        acc = ag.accept_contract(session_id, contract_proposal["message_id"], orchestrator, contract_obj)
        accept_msgs.append(acc)
        jprint(f"RECV ← CONTRACT_ACCEPTANCE ({ag.actor.id} → orchestrator)", acc)

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
        "audience": [a.actor.to_dict() for a in agents],
        "issued_at": utc_now_iso(),
        "not_before": not_before.isoformat().replace("+00:00", "Z"),
        "not_after": not_after.isoformat().replace("+00:00", "Z"),
        "limits": {"max_invocations_per_actor": 3, "max_invocations_total": 20},
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
        session_id=session_id,
        payload={"token": token},
    )
    ok, errors = schema.validate("execution-token.schema.json", token_msg)
    if not ok:
        raise ValueError(f"Token schema errors: {errors}")
    jprint("SEND → EXECUTION_TOKEN (issuer → broadcast)", token_msg)

    # ---------------- Governed execution ----------------
    # Parameters for each action
    prompts = {
        "compose_outline": "Create a structured outline explaining how CPNs relate to CTL/LTL model checking. Use 5–8 bullet points.",
        "write_draft": "Write a ~250 word draft explaining how CPNs relate to CTL/LTL model checking. Clear, technical, no fluff.",
        "review_text": "Review the following text and suggest improvements (accuracy, clarity, structure). Provide bullet points.",
        "summarise_text": "Summarise the final content into a concise 120–160 word explanation.",
    }

    outputs: Dict[str, str] = {}

    # Planner
    for ag in agents:
        action = ag.capability.action
        inv_id = new_uuid()
        params = {"prompt": prompts[action]}
        if action == "review_text":
            params["prompt"] += "\n\nTEXT:\n" + outputs.get("write_draft", "[draft missing]")
        if action == "summarise_text":
            params["prompt"] += "\n\nDRAFT:\n" + outputs.get("write_draft", "") + "\n\nREVIEW:\n" + outputs.get("review_text", "")

        req = make_envelope(
            icnp_version="1.0.0",
            msg_type="execution_request",
            phase="execution",
            sender=orchestrator,
            recipient=ag.actor,
            session_id=session_id,
            payload={
                "request": {
                    "invocation_id": inv_id,
                    "token_id": token["token_id"],
                    "contract_id": contract_id,
                    "action": action,
                    "executor": ag.actor.to_dict(),
                    "requested_at": utc_now_iso(),
                    "nonce": rand_nonce(),
                    "parameters": params,
                }
            },
        )
        ok, errors = schema.validate("execution.schema.json", req)
        if not ok:
            raise ValueError(f"Execution request schema errors: {errors}")
        jprint(f"SEND → EXECUTION_REQUEST ({orchestrator.id} → {ag.actor.id})", req)

        responses = ag.verify_and_execute(req, token_msg, contract_obj)
        for resp in responses:
            if resp["type"] == "execution_result":
                jprint(f"RECV ← EXECUTION_RESULT ({ag.actor.id} → orchestrator)", resp)
                outputs[action] = resp["payload"]["result"]["output"]["text"]
            elif resp["type"] == "audit_event":
                jprint(f"AUDIT ← AUDIT_EVENT ({ag.actor.id})", resp)
            else:
                jprint(f"RECV ← {resp['type']} ({ag.actor.id} → orchestrator)", resp)

    # Print final assembled output
    print("\n" + "#" * 90)
    print("FINAL ARTEFACTS")
    print("#" * 90)
    for k in ["compose_outline", "write_draft", "review_text", "summarise_text"]:
        print(f"\n--- {k} ---\n{outputs.get(k, '')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
