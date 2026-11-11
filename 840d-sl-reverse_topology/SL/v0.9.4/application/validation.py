from __future__ import annotations
from typing import Any, Mapping
from .dto import METHODS, ERROR_CODES

NOT_COMPARABLE_REASONS = {
    "selector_mismatch",
    "representation_mismatch",
    "incomplete_snapshot",
    "identity_mismatch",
    "unsupported_comparison",
}

class ValidationError(ValueError):
    def __init__(self, message: str, violations: list[dict[str, str]] | None = None):
        super().__init__(message)
        self.violations = violations or [{"pointer": "", "code": "invalid", "message": message}]

def _fail(pointer: str, message: str, code: str = "invalid") -> None:
    raise ValidationError(message, [{"pointer": pointer, "code": code, "message": message}])

def _opaque(p: Mapping[str, Any], key: str) -> None:
    value = p.get(key)
    if not isinstance(value, str) or not value or "\x00" in value or len(value) > 4096:
        _fail("/params/" + key, "opaque identifier required")

def validate_request(value: Any) -> None:
    if not isinstance(value, Mapping): _fail("", "request must be an object")
    if value.get("jsonrpc") != "2.0": _fail("/jsonrpc", "jsonrpc must be 2.0")
    if "method" not in value or not isinstance(value["method"], str): _fail("/method", "method is required")
    method = value["method"]
    if "params" not in value or not isinstance(value["params"], Mapping): _fail("/params", "params must be an object")
    p = value["params"]
    if method not in METHODS: return
    allowed = {
      "capabilities.get": set(), "health.get": set(),
      "snapshot.list": {"limit","cursor","filters"},
      "snapshot.get": {"snapshot_id"}, "topology.query": {"snapshot_id","limit","cursor","filters"},
      "topology.reconcile": {"actual_snapshot_id","target_snapshot_id"},
      "evidence.get": {"evidence_id"},
      "event.list": {"limit","cursor","filters","from_event_id","from_offset"},
    }[method]
    unknown = set(p) - allowed
    if unknown: _fail("/params", "unknown parameter: " + sorted(unknown)[0])
    if method in {"capabilities.get", "health.get"} and p: _fail("/params", "params must be empty")
    required = {"snapshot.get": ["snapshot_id"], "topology.query": ["snapshot_id"], "topology.reconcile": ["actual_snapshot_id", "target_snapshot_id"], "evidence.get": ["evidence_id"]}
    for key in required.get(method, []): _opaque(p, key)
    if "cursor" in p: _opaque(p, "cursor")
    if method == "event.list":
        if "from_event_id" in p and "from_offset" in p: _fail("/params", "replay starts are mutually exclusive")
        if "from_event_id" in p: _opaque(p, "from_event_id")
        if "from_offset" in p and (not isinstance(p["from_offset"], int) or isinstance(p["from_offset"], bool) or p["from_offset"] < 0): _fail("/params/from_offset", "from_offset must be a non-negative integer")
    if method in {"snapshot.list", "topology.query", "event.list"} and "limit" in p and (not isinstance(p["limit"], int) or isinstance(p["limit"], bool) or not 1 <= p["limit"] <= 1000): _fail("/params/limit", "limit must be 1..1000")
    if "filters" in p and not isinstance(p["filters"], Mapping): _fail("/params/filters", "filters must be an object")
    if "filters" in p: validate_json_value(p["filters"])

def validate_response(value: Mapping[str, Any], method: str | None = None) -> None:
    if not isinstance(value, Mapping) or value.get("jsonrpc") != "2.0": raise ValidationError("invalid response envelope")
    if ("result" in value) == ("error" in value): raise ValidationError("closed response envelope required")
    if "result" in value:
        if value.get("id") is None: raise ValidationError("success id must be non-null")
        result=value["result"]
        if not isinstance(result, Mapping) or result.get("contract_version") != "api-v1" or result.get("method") != method: raise ValidationError("result method/contract mismatch")
        required={"capabilities.get":{"protocol_version","schema_version","methods","live_acquisition"},"health.get":{"status"},"snapshot.get":{"snapshot"},"evidence.get":{"evidence"},"topology.reconcile":{"reconciliation"},"snapshot.list":{"items","has_more","next_cursor","consistency"},"topology.query":{"items","has_more","next_cursor","consistency"},"event.list":{"items","has_more","next_cursor","consistency","replay"}}
        if method in required and not required[method].issubset(result): raise ValidationError("result fields missing")
    if "error" in value:
        body=value["error"]
        if not isinstance(body, Mapping) or set(body) != {"code","message","data"} or body.get("code") not in ERROR_CODES or not isinstance(body.get("message"), str) or not body["message"] or not isinstance(body.get("data"), Mapping): raise ValidationError("invalid error envelope")
        if body["code"] == "NOT_COMPARABLE":
            data = body["data"]
            allowed = {"reason", "actual_snapshot_id", "target_snapshot_id"}
            if set(data) - allowed or "reason" not in data or data["reason"] not in NOT_COMPARABLE_REASONS:
                raise ValidationError("invalid NOT_COMPARABLE data")
            for key in ("actual_snapshot_id", "target_snapshot_id"):
                if key in data and (not isinstance(data[key], str) or not data[key] or "\x00" in data[key] or len(data[key]) > 4096):
                    raise ValidationError("invalid NOT_COMPARABLE snapshot id")

def validate_event(event: Mapping[str, Any]) -> None:
    required=("event_version","event_id","offset","installation_id","kind","revision","payload")
    # Preserve the pre-v1 offline fixture shape while rejecting all other partial records.
    if set(event) == {"id", "event_id", "offset"}:
        if not isinstance(event["event_id"], str) or not event["event_id"] or not isinstance(event["offset"], int) or isinstance(event["offset"], bool) or event["offset"] < 0:
            raise ValidationError("invalid legacy event envelope")
        return
    if set(event) != set(required) or event.get("event_version") != "event-v1" or not isinstance(event.get("event_id"), str) or not event.get("event_id") or not isinstance(event.get("installation_id"), str) or not event.get("installation_id") or not isinstance(event.get("kind"), str) or not event.get("kind") or not isinstance(event.get("payload"), Mapping): raise ValidationError("invalid event envelope")
    if not isinstance(event["offset"], int) or isinstance(event["offset"], bool) or event["offset"] < 0 or not isinstance(event["revision"], int) or isinstance(event["revision"], bool) or event["revision"] < 0: raise ValidationError("invalid event offsets")

def validate_evidence(evidence: Mapping[str, Any]) -> None:
    required={"evidence_id","artifact_id","artifact_ref","endpoint_identity","observed_at","quality","rule_id","rule_version"}
    missing=required-set(evidence)
    if missing: raise ValidationError("missing evidence fields", [{"pointer":"/"+x,"code":"EVIDENCE_GATE_FAILED","message":"required field"} for x in sorted(missing)])
    if not isinstance(evidence["evidence_id"], str) or not evidence["evidence_id"]: raise ValidationError("invalid evidence_id")
    if ("observed_value" in evidence) == ("observed_absent" in evidence): raise ValidationError("exactly one observation form required")
    ident=evidence["endpoint_identity"]
    if not isinstance(ident, Mapping) or not all(isinstance(ident.get(k), str) and ident[k] for k in ("object_id","kind")): raise ValidationError("invalid endpoint identity")
    ref=evidence["artifact_ref"]
    if not isinstance(ref, Mapping) or not ref: raise ValidationError("invalid artifact reference")

def validate_json_value(value: Any) -> None:
    """Reject filter values that cannot survive the JSON request boundary."""
    try:
        import json
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValidationError("filters must contain JSON-serializable values", [{"pointer":"/params/filters", "code":"invalid", "message":"filters must contain JSON-serializable values"}]) from exc
