\
from __future__ import annotations

import base64
import dataclasses
import hashlib
import hmac
import json
import secrets
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from jsonschema import Draft202012Validator


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
class Actor:
    id: str
    role: str
    display_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {"id": self.id, "role": self.role}
        if self.display_name:
            d["display_name"] = self.display_name
        return d


class SchemaRegistry:
    """Loads and validates messages against the provided JSON schemas."""
    def __init__(self, schemas_path: str):
        from pathlib import Path

        self.schemas_path = Path(schemas_path)
        self._schemas: Dict[str, Dict[str, Any]] = {}
        self._validators: Dict[str, Draft202012Validator] = {}

        # Load all schemas first
        for p in self.schemas_path.glob("*.schema.json"):
            self._schemas[p.name] = json.loads(p.read_text(encoding="utf-8"))

        from referencing import Registry, Resource
        from referencing.jsonschema import DRAFT202012

        registry = Registry()
        for name, schema in self._schemas.items():
            resource = Resource.from_contents(schema, default_specification=DRAFT202012)
            if "$id" in schema:
                registry = registry.with_resource(schema["$id"], resource)
            registry = registry.with_resource(name, resource)

        for name, schema in self._schemas.items():
            self._validators[name] = Draft202012Validator(schema, registry=registry)

    def validate(self, schema_filename: str, message: Dict[str, Any]) -> Tuple[bool, List[str]]:
        v = self._validators[schema_filename]
        errors = [e.message for e in sorted(v.iter_errors(message), key=lambda e: e.path)]
        return (len(errors) == 0), errors


def make_envelope(
    *,
    icnp_version: str,
    msg_type: str,
    phase: str,
    sender: Actor,
    session_id: str,
    payload: Dict[str, Any],
    recipient: Optional[Actor] = None,
    in_reply_to: Optional[str] = None,
    trace: Optional[Dict[str, Any]] = None,
    extensions: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    env: Dict[str, Any] = {
        "icnp_version": icnp_version,
        "type": msg_type,
        "phase": phase,
        "message_id": new_uuid(),
        "session_id": session_id,
        "timestamp": utc_now_iso(),
        "sender": sender.to_dict(),
        "payload": payload,
    }
    if recipient is not None:
        env["recipient"] = recipient.to_dict()
    if in_reply_to is not None:
        env["in_reply_to"] = in_reply_to
    if trace is not None:
        env["trace"] = trace
    if extensions is not None:
        env["extensions"] = extensions
    return env


def sign_token_hmac(token_body: Dict[str, Any], *, secret: bytes, signed_by: str, key_id: str = "demo-key") -> Dict[str, Any]:
    """Returns a Signature object and mutates no inputs."""
    msg = canonical_json(token_body)
    return {
        "alg": "hmac-sha256",
        "value": hmac_sha256_b64(secret, msg),
        "key_id": key_id,
        "signed_by": signed_by,
        "signed_at": utc_now_iso(),
    }


def verify_token_hmac(token_body: Dict[str, Any], signature: Dict[str, Any], *, secret: bytes) -> bool:
    if signature.get("alg") != "hmac-sha256":
        return False
    expected = hmac_sha256_b64(secret, canonical_json(token_body))
    return hmac.compare_digest(signature.get("value", ""), expected)


def make_binding_hashes(intent_payload: Dict[str, Any], contract_obj: Dict[str, Any], capabilities_payload: Dict[str, Any]) -> Dict[str, Any]:
    def wrap(hex_value: str) -> Dict[str, Any]:
        return {"alg": "sha256", "value": hex_value}

    return {
        "intent_hash": wrap(sha256_hex(intent_payload)),
        "contract_hash": wrap(sha256_hex(contract_obj)),
        "capabilities_hash": wrap(sha256_hex(capabilities_payload)),
    }


def rand_nonce() -> str:
    return secrets.token_urlsafe(18)
