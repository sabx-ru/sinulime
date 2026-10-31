"""Stage 2 domain and evidence contracts.

Acquisition remains outside this module; validation is intentionally schema-derived
and does not depend on the optional jsonschema package.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Mapping

from .identity_context import _TRUSTED_KINDS


@dataclass(frozen=True)
class RawObservationRef:
    area: int | None = None; block: int | None = None; unit: int | None = None
    param: int | str | None = None; index: int | str = 0; source: str | None = None
    def to_dict(self) -> dict[str, Any]: return {k: v for k, v in asdict(self).items() if v is not None}

@dataclass(frozen=True)
class ArtifactRef:
    artifact_id: str; source_ref: RawObservationRef; member: str | None = None; byte_range: tuple[int, int] | None = None
    def to_dict(self) -> dict[str, Any]:
        value = {"source_ref": self.source_ref.to_dict()}
        if self.member is not None: value["member"] = self.member
        if self.byte_range is not None: value["byte_range"] = list(self.byte_range)
        return value

@dataclass(frozen=True)
class EndpointIdentity:
    object_id: str; kind: str = "object"; selector: Mapping[str, Any] = field(default_factory=dict); identity_status: str = "unknown"
    def to_dict(self) -> dict[str, Any]: return {"object_id": self.object_id, "kind": self.kind, "selector": dict(self.selector), "identity_status": self.identity_status}

@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str; artifact_ref: ArtifactRef; endpoint_identity: EndpointIdentity; observed_at: str
    quality: str = "ok"; rule_id: str = "observation"; rule_version: str = "1"; observed_value: Any = None
    observed_absent: bool = False; extensions: Mapping[str, Any] = field(default_factory=dict)
    def to_dict(self) -> dict[str, Any]:
        value = asdict(self); value["artifact_id"] = self.artifact_ref.artifact_id
        value["artifact_ref"] = self.artifact_ref.to_dict(); value["endpoint_identity"] = self.endpoint_identity.to_dict()
        if self.observed_value is None and not self.observed_absent: value["observed_absent"] = True
        return value

@dataclass(frozen=True)
class EvidenceEnvelope:
    snapshot_id: str; revision: int; captured_at: str; mode: str; installation_id: str; completeness: str
    evidence: tuple[EvidenceRecord, ...] = ()
    actual: Mapping[str, Any] = field(default_factory=lambda: {"availability":"unavailable", "reason":"not supplied"})
    target: Mapping[str, Any] = field(default_factory=lambda: {"availability":"unavailable", "reason":"not supplied"})
    reconciliation: Mapping[str, Any] = field(default_factory=lambda: {"actual_snapshot_id":None,"target_snapshot_id":None,"status":"not_comparable","reason":"not supplied","items":[],"extensions":{}})
    unresolved: tuple[Mapping[str, Any], ...] = (); extensions: Mapping[str, Any] = field(default_factory=dict)
    installation_identity: Mapping[str, Any] | None = None
    capture_host_identity: Mapping[str, Any] | None = None
    def to_dict(self) -> dict[str, Any]:
        value = {"schema":"sinumerik-core/read-only-topology/v1","snapshot_id":self.snapshot_id,"revision":self.revision,"captured_at":self.captured_at,"mode":self.mode,"installation_id":self.installation_id,"completeness":self.completeness,"actual":dict(self.actual),"target":dict(self.target),"reconciliation":dict(self.reconciliation),"evidence":[x.to_dict() for x in self.evidence],"unresolved":[dict(x) for x in self.unresolved],"extensions":dict(self.extensions)}
        if self.installation_identity is not None:
            value["installation_identity"] = dict(self.installation_identity)
        if self.capture_host_identity is not None:
            value["capture_host_identity"] = dict(self.capture_host_identity)
        return value

_ENDPOINT_KEYS = {"physical_device":{"device_key"},"logical_object":{"logical_key"},"channel":{"channel_kind","ordinal"},"port":{"group","ordinal"},"object":{"object_key"}}

def _nonempty(value: Any) -> bool: return value is not None and value != "" and value != []
def _validate_endpoint(endpoint: Mapping[str, Any], *, stable: bool = False) -> None:
    if not isinstance(endpoint, Mapping) or not _nonempty(endpoint.get("object_id")) or endpoint.get("kind") not in _ENDPOINT_KEYS:
        raise ValueError("endpoint requires non-empty object_id and supported kind")
    selector = endpoint.get("selector")
    if not isinstance(selector, Mapping) or set(selector) != _ENDPOINT_KEYS[endpoint["kind"]]: raise ValueError("endpoint kind/selector is malformed")
    if endpoint["kind"] in {"channel","port"} and (not isinstance(selector.get("ordinal"), int) or selector["ordinal"] < 0): raise ValueError("endpoint ordinal is invalid")
    if endpoint.get("identity_status") not in {"stable", "provisional", "unknown"}: raise ValueError("endpoint identity_status must be stable, provisional, or unknown")
    if stable and endpoint.get("identity_status") != "stable": raise ValueError("confirmed relation requires stable endpoint identities")

def validate_confirmation(record: Mapping[str, Any], evidence_ids: set[str] | None = None) -> None:
    """Validate all records; confirmed records additionally require the evidence gate."""
    if not isinstance(record, Mapping): raise ValueError("graph record must be an object")
    for key in ("id","kind","from","to","status","rule_id","rule_version","checks","evidence_ids","extensions"):
        if key not in record or not _nonempty(record[key]): raise ValueError(f"record requires non-empty {key}")
    if record["status"] not in {"confirmed","reference_only","unresolved","incomplete","not_comparable"}: raise ValueError("invalid record status")
    _validate_endpoint(record["from"], stable=record["status"] == "confirmed"); _validate_endpoint(record["to"], stable=record["status"] == "confirmed")
    if not isinstance(record["checks"], list) or not all(isinstance(x,str) and x for x in record["checks"]): raise ValueError("checks must be non-empty strings")
    if not isinstance(record["evidence_ids"], list) or not all(isinstance(x,str) and x for x in record["evidence_ids"]): raise ValueError("evidence_ids must be non-empty strings")
    if len(record["evidence_ids"]) != len(set(record["evidence_ids"])): raise ValueError("evidence_ids must be unique")
    # A confirmed record must have a supplied, non-empty evidence index. Treat
    # an absent index and an empty index alike: neither can resolve evidence.
    if record["status"] == "confirmed":
        if not evidence_ids or not record["evidence_ids"]:
            raise ValueError("confirmed record requires resolvable evidence")
        if not set(record["evidence_ids"]).issubset(evidence_ids):
            raise ValueError("record references unresolved evidence")
    elif evidence_ids is not None and not set(record["evidence_ids"]).issubset(evidence_ids):
        raise ValueError("record references unresolved evidence")
    if record["status"] == "confirmed" and record.get("confidence", "confirmed") != "confirmed": raise ValueError("confirmed record requires confirmed confidence")

def _graph(graph: Mapping[str, Any], evidence_ids: set[str]) -> None:
    if graph.get("availability") == "unavailable":
        if not _nonempty(graph.get("reason")): raise ValueError("unavailable graph requires reason")
        return
    required = ("objects","channels","ports","connections","relations","extensions")
    if not all(k in graph for k in required): raise ValueError("complete graph fields are required")
    for obj in graph["objects"]:
        if not isinstance(obj, Mapping) or not isinstance(obj.get("identity"), Mapping) or not _nonempty(obj["identity"].get("id")) or not _nonempty(obj.get("object_kind")): raise ValueError("object identity/kind is required")
    for item in list(graph["connections"])+list(graph["relations"]): validate_confirmation(item, evidence_ids)

def _validate_identity_extensions(data: Mapping[str, Any]) -> None:
    installation = data.get("installation_identity")
    if installation is not None:
        if not isinstance(installation, Mapping):
            raise ValueError("installation_identity must be an object")
        status = installation.get("status")
        if status not in {"unknown", "confirmed", "conflict", "provisional"}:
            raise ValueError("invalid installation identity status")
        fields = ("identifier", "source_kind", "source_field", "scope",
                  "stability", "confidence", "evidence_ref")
        for field_name in fields:
            if field_name not in installation:
                raise ValueError(f"installation_identity requires {field_name}")
        for field_name in fields:
            value = installation[field_name]
            if value is not None and not isinstance(value, str):
                raise ValueError(f"installation_identity {field_name} must be a string or null")
        if status == "confirmed":
            required = ("identifier", "source_kind", "source_field", "scope",
                        "stability", "evidence_ref")
            if not all(isinstance(installation[field_name], str) and installation[field_name]
                       for field_name in required):
                raise ValueError("confirmed installation identity requires provenance")
            if installation["source_kind"] not in _TRUSTED_KINDS:
                raise ValueError("confirmed installation identity requires trusted source")
            if installation["confidence"] not in {"high", "confirmed"}:
                raise ValueError("confirmed installation identity requires confidence")
        elif status == "unknown":
            if any(installation[field_name] is not None for field_name in
                   ("identifier", "source_kind", "source_field", "scope",
                    "stability", "evidence_ref")):
                raise ValueError("unknown installation identity cannot carry identity data")
            if installation["confidence"] != "unknown":
                raise ValueError("unknown installation identity requires unknown confidence")
        elif status == "conflict":
            if (installation["identifier"] is not None or
                    installation["source_kind"] != "conflict" or
                    installation["source_field"] != "installation_id" or
                    installation["scope"] != "conflict" or
                    not installation["evidence_ref"] or
                    installation["confidence"] != "unknown"):
                raise ValueError("conflict installation identity requires explicit provenance")
        elif status == "provisional":
            if installation["confidence"] not in {"low", "provisional", "unknown"}:
                raise ValueError("provisional installation identity cannot be confirmed")
            if installation["source_kind"] in _TRUSTED_KINDS:
                raise ValueError("provisional installation identity cannot use trusted source")

    host = data.get("capture_host_identity")
    if host is not None:
        if not isinstance(host, Mapping):
            raise ValueError("capture_host_identity must be an object")
        for field_name in ("host_id", "process_id", "captured_at", "adapter"):
            if field_name in host and host[field_name] is not None and not isinstance(host[field_name], str):
                raise ValueError(f"capture_host_identity {field_name} must be a string or null")
        if "host_id" not in host or not isinstance(host["host_id"], str) or not host["host_id"]:
            raise ValueError("capture_host_identity host_id must be a string")


def validate_envelope(envelope: EvidenceEnvelope | Mapping[str, Any]) -> None:
    data = envelope.to_dict() if hasattr(envelope, "to_dict") else envelope
    if not isinstance(data, Mapping): raise ValueError("envelope must be an object")
    for key in ("schema","snapshot_id","revision","captured_at","mode","installation_id","completeness","actual","target","reconciliation","evidence","unresolved","extensions"):
        if key not in data: raise ValueError(f"envelope requires {key}")
    if data["schema"] != "sinumerik-core/read-only-topology/v1" or not _nonempty(data["snapshot_id"]) or not _nonempty(data["installation_id"]): raise ValueError("invalid envelope identity/schema")
    _validate_identity_extensions(data)
    try: datetime.fromisoformat(str(data["captured_at"]).replace("Z","+00:00"))
    except ValueError as exc: raise ValueError("captured_at must be date-time") from exc
    ids: set[str] = set()
    for item in data["evidence"]:
        for key in ("evidence_id","artifact_id","artifact_ref","endpoint_identity","observed_at","quality","rule_id","rule_version","extensions"):
            if key not in item or not _nonempty(item[key]): raise ValueError(f"evidence requires {key}")
        artifact_ref = item["artifact_ref"]
        if not isinstance(artifact_ref, Mapping): raise ValueError("artifact_ref must be an object")
        # artifact_id is the canonical artifact identity.  A repeated ID in a
        # ref (accepted for legacy payloads) is permitted only when identical.
        if "artifact_id" in artifact_ref and artifact_ref["artifact_id"] != item["artifact_id"]:
            raise ValueError("artifact_id and artifact_ref identity disagree")
        _validate_endpoint(item["endpoint_identity"]); ids.add(item["evidence_id"])
    if len(ids) != len(data["evidence"]): raise ValueError("evidence_id values must be unique within envelope")
    _graph(data["actual"], ids); _graph(data["target"], ids)
    rec=data["reconciliation"]
    for key in ("actual_snapshot_id","target_snapshot_id","status","reason","items","extensions"):
        if key not in rec: raise ValueError(f"reconciliation requires {key}")
    for item in rec["items"]:
        if not all(k in item for k in ("key","change","reason","extensions")): raise ValueError("reconciliation item incomplete")
    for item in data["unresolved"]:
        if item.get("status") != "unresolved" or not _nonempty(item.get("reason")) or "extensions" not in item: raise ValueError("unresolved record incomplete")
