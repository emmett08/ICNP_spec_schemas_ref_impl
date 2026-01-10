from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from jsonschema import Draft7Validator


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_uuid() -> str:
    return str(uuid.uuid4())


def canonical_json(obj: Any) -> str:
    """Canonical JSON for hashing/signing: stable key order, no whitespace."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def hmac_sha256_b64(secret: bytes, message: str) -> str:
    sig = hmac.new(secret, message.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(sig).decode("ascii")


@dataclass(frozen=True)
class Sender:
    id: str
    type: str
    trust_level: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = {"id": self.id, "type": self.type}
        if self.trust_level:
            data["trust_level"] = self.trust_level
        return data


@dataclass(frozen=True)
class Responder:
    id: str
    version: Optional[str] = None
    certifications: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        data = {"id": self.id}
        if self.version:
            data["version"] = self.version
        if self.certifications:
            data["certifications"] = self.certifications
        return data


class SchemaRegistry:
    """Loads and validates messages against the provided JSON schemas."""

    def __init__(self, schemas_path: str):
        from pathlib import Path

        self.schemas_path = Path(schemas_path)
        self._schemas: Dict[str, Dict[str, Any]] = {}
        self._validators: Dict[str, Draft7Validator] = {}

        for p in self.schemas_path.glob("*.schema.json"):
            schema = json.loads(p.read_text(encoding="utf-8"))
            self._schemas[p.name] = schema
            self._validators[p.name] = Draft7Validator(schema)

    def validate(self, schema_filename: str, message: Dict[str, Any]) -> Tuple[bool, List[str]]:
        v = self._validators[schema_filename]
        errors = [e.message for e in sorted(v.iter_errors(message), key=lambda e: e.path)]
        return (len(errors) == 0), errors


def make_intent_message(
    *,
    intent: Dict[str, Any],
    sender: Dict[str, Any],
    icnp_version: str = "1.0",
) -> Dict[str, Any]:
    return {
        "icnp_version": icnp_version,
        "phase": "intent_declaration",
        "message_id": new_uuid(),
        "timestamp": utc_now_iso(),
        "intent": intent,
        "sender": sender,
    }


def make_capability_message(
    *,
    in_reply_to: str,
    capabilities: List[Dict[str, Any]],
    responder: Dict[str, Any],
    limitations: Optional[List[Dict[str, Any]]] = None,
    resource_requirements: Optional[Dict[str, Any]] = None,
    icnp_version: str = "1.0",
) -> Dict[str, Any]:
    msg: Dict[str, Any] = {
        "icnp_version": icnp_version,
        "phase": "capability_disclosure",
        "in_reply_to": in_reply_to,
        "capabilities": capabilities,
        "responder": responder,
    }
    if limitations:
        msg["limitations"] = limitations
    if resource_requirements:
        msg["resource_requirements"] = resource_requirements
    return msg


def make_contract_message(
    *,
    contract_id: str,
    agreed_actions: List[Dict[str, Any]],
    execution_constraints: Dict[str, Any],
    forbidden_actions: Optional[List[Dict[str, Any]]] = None,
    approval_chain: Optional[List[Dict[str, Any]]] = None,
    signatures: Optional[Dict[str, Any]] = None,
    icnp_version: str = "1.0",
) -> Dict[str, Any]:
    msg: Dict[str, Any] = {
        "icnp_version": icnp_version,
        "phase": "contract_negotiation",
        "contract_id": contract_id,
        "agreed_actions": agreed_actions,
        "execution_constraints": execution_constraints,
    }
    if forbidden_actions:
        msg["forbidden_actions"] = forbidden_actions
    if approval_chain:
        msg["approval_chain"] = approval_chain
    if signatures:
        msg["signatures"] = signatures
    return msg


def make_execution_token_message(
    *,
    token_id: str,
    contract_id: str,
    token: str,
    validity: Dict[str, Any],
    binding: Dict[str, Any],
    enforcement: Dict[str, Any],
    icnp_version: str = "1.0",
) -> Dict[str, Any]:
    return {
        "icnp_version": icnp_version,
        "phase": "execution_token",
        "token_id": token_id,
        "contract_id": contract_id,
        "token": token,
        "validity": validity,
        "binding": binding,
        "enforcement": enforcement,
    }


def sign_token_hmac(token_body: Dict[str, Any], *, secret: bytes) -> str:
    return hmac_sha256_b64(secret, canonical_json(token_body))


def verify_token_hmac(token_body: Dict[str, Any], signature: str, *, secret: bytes) -> bool:
    expected = hmac_sha256_b64(secret, canonical_json(token_body))
    return hmac.compare_digest(signature, expected)


def make_demo_token(token_body: Dict[str, Any], *, secret: bytes) -> str:
    payload = base64.urlsafe_b64encode(canonical_json(token_body).encode("utf-8")).decode("ascii").rstrip("=")
    signature = sign_token_hmac(token_body, secret=secret)
    return f"demo.{payload}.{signature}"


def make_binding_hashes(
    intent: Dict[str, Any],
    contract: Dict[str, Any],
    capabilities: List[Dict[str, Any]],
) -> Dict[str, Any]:
    def wrap(obj: Any) -> str:
        return f"sha256:{sha256_hex(obj)}"

    return {
        "intent_hash": wrap(intent),
        "contract_hash": wrap(contract),
        "capability_hashes": [wrap(cap) for cap in capabilities],
    }


def rand_nonce() -> str:
    return secrets.token_urlsafe(18)
