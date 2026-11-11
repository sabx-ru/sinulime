from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping

METHODS = ("capabilities.get", "snapshot.list", "snapshot.get", "topology.query", "topology.reconcile", "evidence.get", "event.list", "health.get")
ERROR_CODES = {"INVALID_REQUEST", "METHOD_NOT_FOUND", "NOT_FOUND", "INVALID_SOURCE", "NOT_COMPARABLE", "REMOTE_BIND_REJECTED", "RESYNC_REQUIRED", "UNRESOLVED_TOPOLOGY", "STORAGE_UNAVAILABLE", "MESSAGE_TOO_LARGE", "INTERNAL_ERROR"}
NOT_COMPARABLE_REASONS = frozenset({
    "selector_mismatch",
    "representation_mismatch",
    "incomplete_snapshot",
    "identity_mismatch",
    "unsupported_comparison",
})

@dataclass(frozen=True)
class Request:
    method: str
    params: Mapping[str, Any]
    id: Any = None
    notification: bool = False

def success(request_id: Any, result: Mapping[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": dict(result)}

def error(request_id: Any, code: str, message: str, data: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if code not in ERROR_CODES: code = "INTERNAL_ERROR"
    if code == "NOT_COMPARABLE":
        if not isinstance(data, Mapping):
            raise ValueError("NOT_COMPARABLE data must be a mapping")
        allowed = {"reason", "actual_snapshot_id", "target_snapshot_id"}
        if set(data) - allowed or not isinstance(data.get("reason"), str) or data["reason"] not in NOT_COMPARABLE_REASONS:
            raise ValueError("invalid NOT_COMPARABLE reason")
        for key in ("actual_snapshot_id", "target_snapshot_id"):
            if key in data:
                value = data[key]
                if not isinstance(value, str) or not value or "\x00" in value or len(value) > 4096:
                    raise ValueError("invalid NOT_COMPARABLE snapshot id")
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message, "data": dict(data or {})}}
