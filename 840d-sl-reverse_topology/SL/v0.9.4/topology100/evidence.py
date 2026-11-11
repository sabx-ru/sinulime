"""v1.0.0 evidence normalization for offline topology captures."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from topology092.model import make_model

VERSION = "1.0.0"
SCHEMA = "read-only-topology/v1.0.0"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def source_ref(area: int, block: int, unit: int, param: int, index: int) -> dict[str, Any]:
    return {"area": area, "block": block, "unit": unit, "param": param, "index": index}


def _read_stats(reads: Path) -> dict[str, Any]:
    statuses: dict[str, int] = {}
    kinds: dict[str, int] = {}
    total = 0
    read_events = 0
    with reads.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            event = json.loads(line)
            total += 1
            kind = str(event.get("kind", "read"))
            kinds[kind] = kinds.get(kind, 0) + 1
            if kind == "read":
                read_events += 1
                status = str(event.get("status"))
                statuses[status] = statuses.get(status, 0) + 1
    return {
        "journal_events": total,
        "read_events": read_events,
        "journal_kinds": kinds,
        "read_statuses": statuses,
    }


def _component_lookup(doc: dict[str, Any]) -> dict[tuple[int, int], dict[str, Any]]:
    return {
        (int(cu), int(component["number"])): component
        for cu, table in doc["topology_actual"].items()
        for component in table["components"]
        if component.get("number") is not None
    }


def _servo_evidence(unit: int, param: int, index: int = 0) -> dict[str, Any]:
    return source_ref(5, 130, unit, param, index)


def _equipment_chain(doc: dict[str, Any], axes: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build only ReadVar-confirmed axis/drive/equipment relations."""
    components = _component_lookup(doc)
    axes_by_identity: dict[tuple[Any, Any, Any], list[dict[str, Any]]] = {}
    for candidate in axes:
        if candidate["status"] == "confirmed":
            key = (candidate["chain"].get("bus_id"), candidate["chain"].get("slave"), candidate["chain"].get("do"))
            axes_by_identity.setdefault(key, []).append(candidate)
    drives: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    for servo in doc["servo_objects"]:
        identity = servo.get("identity") or {}
        key = (identity.get("bus_id"), identity.get("slave"), identity.get("do"))
        axis_candidates = axes_by_identity.get(key, [])
        ambiguous = len(axis_candidates) > 1
        axis = axis_candidates[0] if len(axis_candidates) == 1 else None
        cu = axis["chain"]["cu"] if axis else None
        drive = {
            "unit": servo.get("unit"),
            "name": servo.get("name"),
            "identity": identity,
            "type": servo.get("type"),
            "do_state": servo.get("do_state"),
            "telegram": servo.get("telegram"),
            "status": "confirmed" if axis else "unresolved",
            "confidence": "confirmed" if axis else "unresolved",
            "mapping_status": "ambiguous_mapping" if ambiguous else ("resolved" if axis else "unresolved"),
            "axis_candidates": axis_candidates,
            "axis_unit": axis.get("axis_unit") if axis else None,
            "cu": cu,
            "evidence": {
                "type": _servo_evidence(servo["unit"], 107),
                "name": _servo_evidence(servo["unit"], 199, 0),
                "do_state": _servo_evidence(servo["unit"], 105),
                "telegram": _servo_evidence(servo["unit"], 922),
            },
        }
        drives.append(drive)
        if not axis or cu is None:
            if ambiguous:
                relations.append({"kind": "AXIS_TO_DRIVE", "status": "unresolved", "confidence": "unresolved",
                                  "reason": "ambiguous_mapping", "from": {"axis_candidates": axis_candidates},
                                  "to": {"servo_unit": servo.get("unit"), "identity": identity},
                                  "evidence": {"source": "NCK.ReadVar", "identity": identity}})
            refs = servo.get("refs", {})
            module_refs = servo.get("motor_module_refs", [])
            raw_refs = refs.get("121") or [None]
            module_targets = [raw_refs[i] if i < len(raw_refs) else None for i in range(len(module_refs))] or [raw_refs[0]]
            for index, target in enumerate(module_targets):
                if index < len(module_refs):
                    target = module_refs[index].get("component", target)
                if target in (None, 0, 255, 65535):
                    relations.append({"kind": "DRIVE_TO_MOTOR_MODULE", "status": "unresolved", "confidence": "unresolved",
                                      "reason": "missing_motor_module_reference",
                                      "from": {"servo_unit": servo.get("unit"), "identity": identity},
                                      "to": {"cu": None, "component": target},
                                      "evidence": {"source": "NCK.ReadVar", "reference": _servo_evidence(servo["unit"], 121, index)}})
            continue
        drive_ref = {"cu": cu, "servo_unit": servo["unit"], "bus_id": identity["bus_id"],
                     "slave": identity["slave"], "do": identity["do"]}
        relations.append({"kind": "AXIS_TO_DRIVE", "status": "confirmed", "confidence": "confirmed",
                          "from": {"axis_unit": axis["axis_unit"]}, "to": drive_ref,
                          "evidence": {"source": "NCK.ReadVar", "identity": identity}})
        refs = servo.get("refs", {})
        ref_specs = [("DRIVE_TO_MOTOR_MODULE", "121", i)
                     for i, target in enumerate(servo.get("motor_module_refs", []))]
        if not ref_specs:
            ref_specs = [("DRIVE_TO_MOTOR_MODULE", "121", 0)]
        ref_specs.append(("DRIVE_TO_MOTOR", "131", 0))
        for kind, param_key, index in ref_specs:
            target = (refs.get(param_key) or [None])[index]
            if kind == "DRIVE_TO_MOTOR_MODULE":
                target = (servo.get("motor_module_refs") or [{}])[index].get("component", target) \
                    if index < len(servo.get("motor_module_refs", [])) else target
            if target in (None, 0, 255, 65535):
                relations.append({"kind": kind, "status": "unresolved", "confidence": "unresolved",
                                  "reason": "missing_motor_module_reference" if kind == "DRIVE_TO_MOTOR_MODULE" else "missing_reference",
                                  "from": drive_ref, "to": {"cu": cu, "component": target},
                                  "evidence": {"source": "NCK.ReadVar", "reference": _servo_evidence(servo["unit"], int(param_key), index)}})
                continue
            component = components.get((cu, target))
            relations.append({"kind": kind,
                              "status": "confirmed" if component else "unresolved",
                              "confidence": "confirmed" if component else "unresolved",
                              "from": drive_ref,
                              "to": {"cu": cu, "component": target},
                              "evidence": {"source": "NCK.ReadVar", "reference": _servo_evidence(servo["unit"], int(param_key), index)}})
        for sensor in servo.get("sensor_refs", []):
            index = sensor.get("source_index")
            valid_index = type(index) is int and index >= 0
            mapping_ok = sensor.get('mapping_status') == 'resolved' and valid_index
            if not valid_index:
                # Evidence references require the original non-negative integer source index.
                # Preserve the record as unresolved, but do not substitute its filtered position.
                reference = None
            else:
                reference = _servo_evidence(servo["unit"], 141, index)
            target = sensor.get("component")
            component = components.get((cu, target)) if target is not None else None
            relation_status = 'confirmed' if component and mapping_ok else 'unresolved'
            relations.append({'kind': 'DRIVE_TO_SENSOR_MODULE',
                              'status': relation_status,
                              'confidence': 'confirmed' if component and mapping_ok else 'unresolved',
                              "from": drive_ref,
                              "to": {"cu": cu, "component": target},
                              "evidence": {"source": "NCK.ReadVar", "reference": reference,
                                           "source_index": index,
                                           "state": sensor.get("state"),
                                           "mapping_status": sensor.get("mapping_status"),
                                           "mapping_reason": sensor.get("mapping_reason")}})
            enc = sensor.get("encoder")
            enc_index = sensor.get("encoder_source_index")
            enc_valid = type(enc_index) is int and enc_index >= 0
            if enc not in (None, 0, 255, 65535):
                enc_component = components.get((cu, enc))
                enc_ok = enc_component and mapping_ok and enc_valid
                relations.append({'kind': 'SENSOR_TO_ENCODER',
                                  'status': 'confirmed' if enc_ok else 'unresolved',
                                  'confidence': 'confirmed' if enc_ok else 'unresolved',
                                  "from": {"cu": cu, "component": target},
                                  "to": {"cu": cu, "component": enc},
                                  "evidence": {"source": "NCK.ReadVar",
                                               "reference": _servo_evidence(servo["unit"], 142, enc_index) if enc_valid else None,
                                               "source_index": enc_index,
                                               "mapping_status": sensor.get("mapping_status"),
                                               "mapping_reason": sensor.get("mapping_reason")}})
    return drives, relations

def build_evidence(reads: str | Path, sdb: str | Path | None = None) -> dict[str, Any]:
    reads_path = Path(reads)
    doc = make_model(reads_path, sdb)
    stats = _read_stats(reads_path)

    components = []
    for cu, table in doc["topology_actual"].items():
        for component in table["components"]:
            components.append({
                "identity": {"context": "CU", "cu": int(cu), "component": component.get("number")},
                "name": component.get("name"),
                "type_code": component.get("type_code"),
                "device_class": component.get("device_class"),
                "device_id": component.get("device_id"),
                "status": "incomplete" if component.get("incomplete") else "confirmed",
                "confidence": "confirmed" if not component.get("incomplete") else "unresolved",
                "evidence": {"source": "NCK.ReadVar", "parameter": "r9901/r9903"},
            })

    connections = []
    for edge in doc["cables_actual"]["edges"]:
        connections.append({
            "kind": "DRIVE_CLIQ_CABLE",
            "status": "confirmed",
            "confidence": "confirmed",
            "from": {
                "cu": edge["cu"], "component": edge["from"],
                "port_ordinal": edge["from_group_port_ordinal"],
            },
            "to": {
                "cu": edge["cu"], "component": edge["to"],
                "port_ordinal": edge["to_group_port_ordinal"],
            },
            "evidence": {
                "source": "NCK.ReadVar",
                "rule": "reciprocal_component_group1",
                "peer_interface_selector": edge.get("peer_interface_selector"),
                "reverse_selector": edge.get("reverse_selector"),
            },
        })
    for relation in doc["cables_actual"]["relations"]:
        connections.append({
            "kind": relation["type"],
            "status": "reference_only",
            "confidence": "probable",
            "from": {"cu": relation["cu"], "component": relation["from"]},
            "to": {"cu": relation["cu"], "component": relation["to"]},
            "evidence": {"source": "NCK.ReadVar", "group": relation["group"],
                         "source_ordinal": relation["source_ordinal"]},
        })

    axes = []
    for axis in doc["axes"]:
        status = axis.get("status", "unresolved")
        axes.append({
            "axis_unit": axis.get("axis_unit"),
            "name": axis.get("name"),
            "status": "confirmed" if status == "VERIFIED_BY_NCK_SDB_CU" else "unresolved",
            "confidence": "confirmed" if status == "VERIFIED_BY_NCK_SDB_CU" else "unresolved",
            "chain": {
                "cu": axis.get("cu"), "do": axis.get("do"),
                "bus_id": axis.get("bus_id"), "slave": axis.get("slave"),
                "slot": axis.get("slot"), "do_type": axis.get("do_type"),
            },
            "evidence": {
                "source": "NCK.ReadVar+SDB",
                "md30110": source_ref(3, 26, axis["axis_unit"], 30110, 0),
                "md13050": source_ref(3, 26, axis["axis_unit"], 13050, 0),
                "md13060": source_ref(3, 26, axis["axis_unit"], 13060, 0),
            },
        })

    drives, equipment_relations = _equipment_chain(doc, axes)
    connections.extend(equipment_relations)

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "provenance": {"reads": str(reads_path), "sdb": str(sdb) if sdb else None,
                       "reads_sha256": sha256_file(reads_path)},
        "summary": {**doc["summary"], **stats,
                    "component_records": len(components),
                    "connection_records": len(connections),
                    "axis_records": len(axes),
                    "drive_records": len(drives),
                    "equipment_relation_records": len(equipment_relations)},
        "axes": axes,
        "drives": drives,
        "components": components,
        "connections": connections,
        "unresolved_ports": doc["cables_actual"].get("unresolved_ports", []),
        "mapping_problems": doc.get("mapping_problems", []),
    }


def write_evidence(doc: dict[str, Any], output: str | Path, *, installation_id: str = "legacy-installation") -> Path:
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    (out / "evidence.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "summary.json").write_text(json.dumps(doc["summary"], ensure_ascii=False, indent=2), encoding="utf-8")
    # Stage 2 is additive: the legacy files above remain byte-compatible in shape.
    from .adapter_legacy import project_legacy
    envelope = project_legacy(doc, snapshot_id=doc.get("provenance", {}).get("reads_sha256", "legacy-replay"),
                              installation_id=installation_id)
    (out / "evidence.v1.json").write_text(json.dumps(envelope.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def compare_summaries(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    fields = ["cu_count", "axes_active", "axes_verified", "hw_slot_count",
              "physical_actual_edges", "cu_link_pairs", "topology_all_tlv_complete"]
    return {field: {"v0.9.4": old.get(field), "v1.0.0": new.get(field),
                    "equal": old.get(field) == new.get(field)} for field in fields}
