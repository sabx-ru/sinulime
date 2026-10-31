from __future__ import annotations
import base64, hashlib, json
from typing import Any, Mapping
from .errors import ResyncRequired


def _token(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw + b"." + hashlib.sha256(raw).digest()).decode().rstrip("=")


def make_cursor(method: str, filters: Mapping[str, Any], position: int, *, consistency="snapshot", installation="", schema="api-v1", retention=0) -> str:
    if not isinstance(position, int) or isinstance(position, bool) or position < 0:
        raise ValueError("cursor position must be a non-negative integer")
    return _token({"v": 1, "method": method, "filters": dict(filters), "position": position,
                   "consistency": consistency, "installation": installation,
                   "schema": schema, "retention": retention})


def read_cursor(token: str, method: str, filters: Mapping[str, Any], *, consistency="snapshot", installation="", schema="api-v1", retention=0) -> int:
    try:
        if not isinstance(token, str) or not token:
            raise ValueError
        raw = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
        body, digest = raw.rsplit(b".", 1)
        data = json.loads(body)
        if not isinstance(data, dict) or hashlib.sha256(body).digest() != digest:
            raise ValueError
        expected = {"v": 1, "method": method, "filters": dict(filters),
                    "consistency": consistency, "installation": installation,
                    "schema": schema, "retention": retention}
        if any(data.get(k) != v for k, v in expected.items()):
            raise ValueError
        position = data["position"]
        if not isinstance(position, int) or isinstance(position, bool) or position < 0:
            raise ValueError
        return position
    except Exception as exc:
        raise ResyncRequired("cursor is expired or incompatible", {
            "earliest_retained_offset": 0, "requested_from_event_id": None,
            "requested_from_offset": None, "authoritative_snapshot_ids": [],
            "reason": "cursor_mismatch"}) from exc
