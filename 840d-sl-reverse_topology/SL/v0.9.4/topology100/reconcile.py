"""Pure Actual/Target reconciliation; no acquisition or persistence."""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, Mapping

STATUSES = {"same", "added", "removed", "changed", "unresolved", "not_comparable"}
NOT_COMPARABLE_REASONS = frozenset({
    "selector_mismatch",
    "representation_mismatch",
    "incomplete_snapshot",
    "identity_mismatch",
    "unsupported_comparison",
})


def validate_not_comparable_reason(reason: str) -> str:
    if reason not in NOT_COMPARABLE_REASONS:
        raise ValueError("unknown NOT_COMPARABLE reason")
    return reason


def unavailable(reason: str) -> dict[str, str]:
    if not reason:
        raise ValueError("unavailable reason is required")
    return {"availability": "unavailable", "reason": reason}


def _identity(item: Mapping[str, Any]) -> str:
    identity = item.get("identity") or {}
    return str(item.get("id") or identity.get("object_id") or "")


def _selector(item: Mapping[str, Any]) -> Any:
    return item.get("selector", (item.get("identity") or {}).get("selector", {}))


def reconcile(actual: Mapping[str, Any], target: Mapping[str, Any], *, key: Callable[[Mapping[str, Any]], str] | None = None) -> dict[str, Any]:
    """Compare snapshots without losing duplicate or selector-ambiguous records."""
    if actual.get("availability") == "unavailable" or target.get("availability") == "unavailable":
        return {"items": [], "status": "not_comparable", "reason": "incomplete_snapshot", "extensions": {}}
    key = key or _identity
    left_items, right_items = list(actual.get("items", [])), list(target.get("items", []))
    left = defaultdict(list); right = defaultdict(list)
    for item in left_items: left[key(item)].append(item)
    for item in right_items: right[key(item)].append(item)
    items: list[dict[str, Any]] = []
    ambiguous = set()
    for name in set(left) | set(right):
        if not name or len(left[name]) > 1 or len(right[name]) > 1:
            ambiguous.add(name)
            records = max(len(left[name]), len(right[name]))
            for index in range(records):
                items.append({"key": f"{name or 'unknown'}#{index}", "change": "unresolved", "actual_ref": name if index < len(left[name]) else None,
                              "target_ref": name if index < len(right[name]) else None, "reason": "ambiguous_mapping", "extensions": {}})
            continue
        a, t = (left[name] or [None])[0], (right[name] or [None])[0]
        if a is not None and t is not None and _selector(a) != _selector(t):
            change, reason = "not_comparable", "selector_mismatch"
        elif a is None: change, reason = "added", None
        elif t is None: change, reason = "removed", None
        elif a == t: change, reason = "same", None
        else: change, reason = "changed", None
        items.append({"key": name, "change": change, "actual_ref": name if a is not None else None,
                      "target_ref": name if t is not None else None, "reason": reason, "extensions": {}})
    if not items:
        status = "same"
    elif any(i["change"] == "unresolved" for i in items): status = "unresolved"
    elif any(i["change"] == "not_comparable" for i in items): status = "not_comparable"
    elif all(i["change"] == "same" for i in items): status = "same"
    else: status = "changed"
    reason = next((i["reason"] for i in items if i["reason"]), None)
    if reason is not None and reason not in {"ambiguous_mapping", "selector_mismatch"}:
        validate_not_comparable_reason(reason)
    return {"items": sorted(items, key=lambda i: (i["key"], i["change"])), "status": status,
            "reason": reason, "extensions": {}}


def reconcile_snapshots(actual: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, Any]:
    return reconcile(actual, target)

