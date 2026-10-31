"""Additive projection from legacy evidence into the schema-compatible v1 envelope."""
from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from .contracts import ArtifactRef, EndpointIdentity, EvidenceEnvelope, EvidenceRecord, RawObservationRef
from .identity import provisional_identity_id, published_identity_id

def _timestamp() -> str: return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
def _endpoint(kind: str, key: str, *, installation_id: str, snapshot_id: str,
              source_identity: dict[str, Any] | None = None) -> dict[str, Any]:
    selector = {"logical_key": key} if kind == "logical_object" else {"object_key": key}
    if source_identity is not None:
        object_id = published_identity_id("v1", installation_id, kind, source_identity)
        status = "stable"
    else:
        object_id = provisional_identity_id("v1", installation_id, snapshot_id, kind, selector)
        status = "provisional"
    return {"object_id": object_id, "kind": kind, "selector": selector, "identity_status": status}
def _evidence(eid: str, endpoint: dict[str, Any], value: Any, index: int, source: dict[str, Any] | None = None) -> EvidenceRecord:
    ref = RawObservationRef(index=source.get("index", index) if source else index, source=source.get("source") if source else None,
                            area=source.get("area") if source else None,
                            block=source.get("block") if source else None,
                            unit=source.get("unit") if source else None,
                            param=source.get("param") if source else None)
    return EvidenceRecord(eid, ArtifactRef(f"artifact-{eid}", ref), EndpointIdentity(endpoint["object_id"], endpoint["kind"], endpoint["selector"], endpoint["identity_status"]), _timestamp(), observed_value=value, extensions={"source":"legacy_projection", "relation_source": source or "legacy_record"})

def project_legacy(legacy: dict[str, Any], *, snapshot_id: str = "legacy-replay", installation_id: str = "legacy-installation") -> EvidenceEnvelope:
    records: list[EvidenceRecord] = []; objects: list[dict[str, Any]] = []; endpoint_by_key: dict[str, dict[str, Any]] = {}
    def add_object(key: str, name: Any, status: str = "confirmed") -> dict[str, Any]:
        if key in endpoint_by_key: return endpoint_by_key[key]
        ep = _endpoint("logical_object", key, installation_id=installation_id, snapshot_id=snapshot_id); endpoint_by_key[key] = ep
        objects.append({"identity":{"id":ep["object_id"],"identity_status":ep["identity_status"],"source_key":key,"extensions":{}},"object_kind":"logical_object","status":status,"name":name,"physical_device_id":None,"extensions":{"legacy":True}})
        return ep
    def add_ev(label: str, ep: dict[str, Any], value: Any, source: dict[str, Any] | None = None) -> str:
        eid = f"legacy-{hashlib.sha256(label.encode()).hexdigest()[:20]}"; records.append(_evidence(eid,ep,value,len(records),source)); return eid
    for index, axis in enumerate(legacy.get("axes", [])):
        key=f"axis:{axis.get('axis_unit',index)}"
        source = axis.get("evidence", {}).get("md30110")
        has_exact_source = isinstance(source, dict) and all(
            source.get(field) is not None for field in ("area", "block", "unit", "param", "index")
        )
        status = "confirmed" if axis.get("status") == "confirmed" and has_exact_source else "reference_only"
        ep=add_object(key,axis.get("name"),status)
        add_ev(key,ep,axis.get("name"),source=({**source, "source": "NCK.ReadVar+SDB"} if has_exact_source else None))
    for index, component in enumerate(legacy.get("components", [])):
        ident=component.get("identity",{}); key=f"component:{ident.get('context','CU')}:{ident.get('cu')}:{ident.get('component',index)}"
        ep=add_object(key,component.get("name"),component.get("status","unresolved"))
    for index, drive in enumerate(legacy.get("drives", [])):
        ident=drive.get("identity",{}); key=f"drive:{drive.get('unit',index)}:{ident.get('bus_id')}:{ident.get('slave')}:{ident.get('do')}"
        ep=add_object(key,drive.get("name"),drive.get("status","unresolved"))
    conns=[]; unresolved=[]
    for index, old in enumerate(legacy.get("connections", [])):
        fr=old.get("from",{}); to=old.get("to",{})
        fk=f"component:{fr.get('cu','?')}:{fr.get('component',fr.get('axis_unit','?'))}"; tk=f"component:{to.get('cu','?')}:{to.get('component',to.get('axis_unit','?'))}"
        fep=add_object(fk,None,"unresolved"); tep=add_object(tk,None,"unresolved")
        old_evidence = old.get("evidence") if isinstance(old.get("evidence"), dict) else {}
        source = old_evidence.get("source_ref") if isinstance(old_evidence.get("source_ref"), dict) else None
        eid = add_ev(f"connection:{index}:{fk}:{tk}", fep, old, source=source)
        status=old.get("status") if old.get("status") in {"confirmed","reference_only","unresolved","incomplete"} else "unresolved"
        if status == "confirmed" and (old.get("confidence") != "confirmed" or source is None): status="reference_only" if old.get("confidence") == "confirmed" else "unresolved"
        if status == "confirmed" and (fep["identity_status"] != "stable" or tep["identity_status"] != "stable"):
            status = "reference_only"
        record={"id":f"legacy-connection-{index}","kind":str(old.get("kind") or "legacy_connection"),"from":fep,"to":tep,"status":status,"confidence":old.get("confidence","unresolved") if status!="confirmed" else "confirmed","rule_id":"legacy_projection","rule_version":"1","checks":["legacy_record"],"evidence_ids":[eid],"extensions":{"legacy":True}}
        conns.append(record)
        if status == "unresolved": unresolved.append({"reason":"missing_evidence","status":"unresolved","evidence_ids":[eid],"extensions":{"record":index}})
    graph={"objects":objects,"channels":[],"ports":[],"connections":conns,"relations":[],"extensions":{"projection":"legacy"}}
    reconciliation={"actual_snapshot_id":snapshot_id,"target_snapshot_id":snapshot_id,"status":"same","reason":None,"items":[],"extensions":{"projection":"legacy_same_snapshot"}}
    summary=legacy.get("summary",{}); complete=bool(summary.get("read_statuses",{}).get("ok"))
    return EvidenceEnvelope(snapshot_id=snapshot_id,revision=0,captured_at=_timestamp(),mode="replay",installation_id=installation_id,completeness="complete" if complete else "partial",evidence=tuple(records),actual=graph,target=json.loads(json.dumps(graph)),reconciliation=reconciliation,unresolved=tuple(unresolved),extensions={"legacy_schema":legacy.get("schema"),"projection":"topology_graph"})

def project_legacy_file(path: str | Path, **kwargs: Any) -> EvidenceEnvelope:
    return project_legacy(json.loads(Path(path).read_text(encoding="utf-8")), **kwargs)
