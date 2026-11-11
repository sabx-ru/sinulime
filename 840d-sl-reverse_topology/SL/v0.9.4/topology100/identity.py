"""Deterministic identity construction for topology domain objects."""
from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from typing import Any
from uuid import NAMESPACE_URL, uuid5

NAMESPACE = uuid5(NAMESPACE_URL, "sinumerik-core")


_EXPONENT = re.compile(r"e([+-])0+(\d+)$")


def _number(value: int | float) -> str:
    """Return the project numeric subset of canonical JSON.

    This is deliberately an explicit normalized rule, not a claim of full
    RFC 8785 compliance: finite integral floats are rendered as integers;
    other finite floats use Python's shortest round-trippable spelling, with
    a normalized exponent. JSON numbers remain numbers (never quoted).
    """
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite number is not valid canonical JSON")
        if value == 0.0:
            return "0"
        if value.is_integer():
            return str(int(value))
        # Python's float repr is the shortest round-trip representation. Normalize
        # exponent spelling as B2-PJCS-1 requires (lowercase, no plus/zero pad).
        text = repr(value).lower()
        if "e" in text:
            mantissa, exponent = text.split("e", 1)
            text = f"{mantissa}e{int(exponent)}"
        return text
    if isinstance(value, int):
        return str(value)
    raise TypeError(f"unsupported canonical JSON number: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    """Serialize deterministically using the documented normalized rule."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return _number(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("canonical JSON object keys must be strings")
        return "{" + ",".join(
            canonical_json(k) + ":" + canonical_json(value[k])
            for k in sorted(value)
        ) + "}"
    if isinstance(value, list):
        return "[" + ",".join(canonical_json(v) for v in value) + "]"
    raise TypeError(f"unsupported canonical JSON value: {type(value).__name__}")


def _require(value: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"missing {field}")
    return value


def _source(value: Mapping[str, Any] | None, field: str) -> str:
    if not isinstance(value, Mapping):
        raise ValueError(f"missing {field}")
    return canonical_json(value)


def _schema(value: str) -> str:
    if value != "v1":
        raise ValueError("unsupported schema_version; only v1 is supported")
    return value


def published_identity_id(schema_version: str, installation_id: str, kind: str,
                          source_identity: Mapping[str, Any]) -> str:
    name = "|".join((_schema(schema_version), _require(installation_id, "installation_id"),
                     _require(kind, "kind"), _source(source_identity, "source_identity")))
    return str(uuid5(NAMESPACE, name))


def provisional_identity_id(schema_version: str, installation_id: str, snapshot_id: str,
                            kind: str, source_observation: Mapping[str, Any]) -> str:
    name = "|".join((_schema(schema_version), _require(installation_id, "installation_id"),
                     _require(snapshot_id, "snapshot_id"), "provisional", _require(kind, "kind"),
                     _source(source_observation, "source_observation")))
    return str(uuid5(NAMESPACE, name))


def identity_id(kind: str, source_identity: Mapping[str, Any] | None = None, *, provisional_key: str | None = None) -> tuple[str, str]:
    """Legacy wrapper, explicitly retained for legacy callers."""
    if source_identity is not None:
        return str(uuid5(NAMESPACE, canonical_json({"kind": kind, "identity": dict(source_identity)}))), "stable"
    if provisional_key is None:
        raise ValueError("missing source identity requires an explicit provisional key")
    return str(uuid5(NAMESPACE, canonical_json({"kind": kind, "provisional": provisional_key}))), "provisional"

identity_id.legacy = True


def endpoint_identity(kind: str, source_identity: Mapping[str, Any] | None = None, *, provisional_key: str | None = None) -> dict[str, Any]:
    object_id, status = identity_id(kind, source_identity, provisional_key=provisional_key)
    return {"object_id": object_id, "kind": kind, "selector": dict(source_identity or {}), "identity_status": status}
