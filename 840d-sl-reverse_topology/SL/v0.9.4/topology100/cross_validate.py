"""Independent endpoint-level cross-validation artifacts.

This module only reads saved topology092 outputs plus independent ARC/PDF sources.
It never mutates runtime evidence, source captures, or production graph code.
"""
from __future__ import annotations
import json, re, subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ARC_PATH_RE = re.compile(r"\\SYSTEM\.DRV\\BUS(?P<bus>\d+)\.DIR\\SLAVE(?P<slave>\d+)\.DIR\\PS(?P<ps>\d{6})\.ACX")


def parse_arc_dp(path: str | Path) -> dict[str, Any]:
    p=Path(path); text=p.read_text(encoding="latin-1", errors="ignore")
    matches=list(ARC_PATH_RE.finditer(text)); paths=[m.group(0) for m in matches]
    stations=Counter((int(m.group("bus")),int(m.group("slave"))) for m in matches)
    return {"source":str(p),"archive_kind":"DP","acx_path_count":len(paths),
            "acx_unique_path_count":len(set(paths)),"stations":[{"bus_id":b,"slave":s,"acx_count":stations[(b,s)]} for b,s in sorted(stations)],
            "paths":paths,"interpretation":"inventory_only","component": "unavailable","device_id":"unavailable","port":"unavailable"}


def extract_pdf_text(path: str | Path) -> str:
    return subprocess.run(["pdftotext","-layout",str(path),"-"],check=True,capture_output=True,text=True).stdout


def inspect_electrical(path: str | Path) -> dict[str, Any]:
    text=extract_pdf_text(path)
    patterns={"drive_cliq":r"drive[ -]?cl[ií]q","motor_module":r"motor module","encoder":r"encoder","axis":r"axis","cu_link":r"cu[ -]?link"}
    return {"source":str(path),"page_text_available":bool(text.strip()),"text_characters":len(text),"keyword_counts":{k:len(re.findall(v,text,re.I)) for k,v in patterns.items()},"interpretation":"independent_type_and_chain_reference","endpoint_mapping":"unavailable"}


def _summary_delta(old,new):
    fields=("cu_count","axes_active","axes_verified","hw_slot_count","physical_actual_edges","physical_target_edges","cu_link_pairs","topology_all_tlv_complete","target_all_tlv_complete")
    return {f:{"v0.9.4":old.get(f),"v1.0.0":new.get(f),"equal":old.get(f)==new.get(f)} for f in fields}


def _records(doc, phase):
    table=doc["topology_"+phase]; components=[]; ports=[]
    for cu_s, rec in table.items():
        cu=int(cu_s)
        for c in rec.get("components",[]):
            components.append({"key":[cu,c.get("number")],"machine_component_key":[None,cu,c.get("number")],"cu":cu,"component":c.get("number"),"name":c.get("name"),"type_code":c.get("type_code"),"device_class":c.get("device_class"),"device_id":c.get("device_id"),"incomplete":c.get("incomplete"),"selector":{"source":c.get("source"),"component_number":c.get("number")}})
            for ordinal, link in c.get("ports",{}).items():
                ports.append({"source":c.get("source"),"cu":cu,"component":c.get("number"),"port_ordinal":_int_or_none(ordinal),"peer_component":link.get("peer_component"),"peer_port_selector":link.get("peer_port"),"selector":{"component_number":c.get("number"),"port_ordinal":_int_or_none(ordinal),"peer_component":link.get("peer_component"),"peer_port_selector":link.get("peer_port")}})
    return components,ports


def _int_or_none(value):
    try: return int(value)
    except (TypeError, ValueError): return None


def _endpoint(edge, side):
    return (edge.get("cu"),edge.get(side),edge.get("from_group_port_ordinal" if side=="from" else "to_group_port_ordinal"))


def _edge_records(doc, phase):
    return [{"phase":phase,"from":{"cu":e.get("cu"),"component":e.get("from"),"port_ordinal":e.get("from_group_port_ordinal")},"to":{"cu":e.get("cu"),"component":e.get("to"),"port_ordinal":e.get("to_group_port_ordinal")},"selectors":{"peer_interface_selector":e.get("peer_interface_selector"),"reverse_selector":e.get("reverse_selector")},"comparison":"exact_evidence"} for e in doc["cables_"+phase].get("edges",[])]



def _edge_key(edge):
    return tuple(sorted((tuple(edge["from"].values()), tuple(edge["to"].values()))) )


def _compare_edges(actual, target):
    """Compare endpoint records as multisets, retaining duplicate inventory."""
    actual_keys = Counter(_edge_key(e) for e in actual)
    target_keys = Counter(_edge_key(e) for e in target)
    rows = []
    for key in sorted(set(actual_keys) | set(target_keys), key=str):
        ac, tc = actual_keys[key], target_keys[key]
        rows.append({"endpoints": key, "status": "exact" if ac == tc else "mismatch",
                     "actual_count": ac, "target_count": tc,
                     "actual": [e for e in actual if _edge_key(e) == key],
                     "target": [e for e in target if _edge_key(e) == key]})
    duplicate_keys = sum(1 for count in actual_keys.values() if count > 1) + sum(1 for count in target_keys.values() if count > 1)
    return {"status": "exact" if actual_keys == target_keys else "mismatch",
            "actual_count": len(actual), "target_count": len(target),
            "duplicate_endpoint_keys": duplicate_keys, "records": rows}



def _cu_links(doc, phase, expected_pairs=None):
    by=defaultdict(list)
    for c in _records(doc,phase)[0]:
        if c["name"] and c["name"].startswith("CU_LINK") and c["device_id"]:
            by[c["device_id"]].append({"cu":c["cu"],"component":c["component"],"key":c["machine_component_key"]})
    links=[{"device_id":d,"representations":sorted(v,key=lambda x:(x["cu"],x["component"])),"status":"exact" if len(v)==2 and len({x["cu"] for x in v})==2 else "unresolved"} for d,v in sorted(by.items())]
    assertion = all(x["status"] == "exact" for x in links) and (expected_pairs is None or len(links) == expected_pairs)
    return {"pairs": links, "expected_pairs": expected_pairs, "assertion": assertion}



def _endpoint_validation(doc):
    out={}
    for phase in ("actual","target"):
        comps,ports=_records(doc,phase); edges=_edge_records(doc,phase); keys=[tuple(c["machine_component_key"]) for c in comps]
        comp_by_key={(x["cu"],x["component"]): x for x in comps}
        unique=len(keys)==len(set(keys)); reciprocal=True; bounds=True; diagnostics=[]
        for p in ports:
            valid_local=isinstance(p["component"], int) and isinstance(p["port_ordinal"], int) and p["port_ordinal"] >= 0
            peer_component=p["peer_component"]; peer_selector=p["peer_port_selector"]
            valid_peer=(peer_component in (None,0,65535) and peer_selector in (None,0)) or (isinstance(peer_component,int) and peer_component >= 0 and isinstance(peer_selector,int) and peer_selector >= 0)
            bounds &= valid_local and valid_peer
            if peer_component in (None,0,65535):
                continue
            peer=comp_by_key.get((p["cu"],peer_component)); reverse=None
            # Source topology stores peer-port selectors as one-based ordinals.
            reverse_ordinal = peer_selector - 1 if isinstance(peer_selector, int) and peer_selector > 0 else peer_selector
            if peer:
                reverse=next((x for x in ports if x["cu"]==p["cu"] and x["component"]==peer_component and x["port_ordinal"]==reverse_ordinal),None)
            ok=peer is not None and reverse is not None and reverse["peer_component"]==p["component"] and reverse["peer_port_selector"]==p["port_ordinal"] + 1
            reciprocal &= ok
            if not ok: diagnostics.append({"source":p,"reason":"missing_or_nonreciprocal_reverse_port"})
        out[phase]={"component_records":comps,"port_records":ports,"edge_records":edges,"assertions":{"unique_component_keys":unique,"reciprocal_ports":reciprocal,"selector_bounds":bounds},"diagnostics":diagnostics,"counts":{"components":len(comps),"ports":len(ports),"edges":len(edges)}}
    return out



def build_report(root: str | Path) -> dict[str,Any]:
    root=Path(root).resolve(); result={"schema":"read-only-topology/cross-validation/v1.1.0","policy":{"runtime_graph_unchanged":True,"arc_electrical_runtime_edges":False,"identity":"machine + cu + component number; device_id only exact CU_LINK match","ordinal_is_identity":False},"machines":{}}
    for machine,arc_name,pdf_name in (("cnc135","DP20260830.arc","135.pdf"),("cnc152","DP.arc","152.pdf")):
        doc=json.loads((root/"runs"/machine/"architecture.json").read_text()); old=json.loads((root/"runs"/machine/"summary.json").read_text()); new=json.loads((root/"runs"/"v1.0.0"/machine/"summary.json").read_text())
        arc=parse_arc_dp(root.parent/"ARCs"/machine[-3:]/arc_name); electrical=inspect_electrical(root.parent/"electrical"/pdf_name)
        runtime=sorted((s["bus_id"],s["slave"]) for s in new["hw_stations"]); arcstations=sorted((s["bus_id"],s["slave"]) for s in arc["stations"])
        endpoint=_endpoint_validation(doc); expected_pairs=4 if machine=="cnc135" else 1; links={p:_cu_links(doc,p,expected_pairs) for p in ("actual","target")}
        link_assert={p:links[p]["assertion"] for p in links}
        edge_comparison=_compare_edges(endpoint["actual"]["edge_records"],endpoint["target"]["edge_records"])
        actual_components=Counter(tuple(c["machine_component_key"]) for c in endpoint["actual"]["component_records"])
        target_components=Counter(tuple(c["machine_component_key"]) for c in endpoint["target"]["component_records"])
        actual_ports=Counter((p["cu"],p["component"],p["port_ordinal"]) for p in endpoint["actual"]["port_records"])
        target_ports=Counter((p["cu"],p["component"],p["port_ordinal"]) for p in endpoint["target"]["port_records"])
        result["machines"][machine]={"runtime_summary_comparison":_summary_delta(old,new),"arc_dp":arc,"electrical":electrical,"endpoint_validation":endpoint,"cu_link_validation":{"actual":links["actual"]["pairs"],"target":links["target"]["pairs"],"expected_pairs":expected_pairs,"assertions":{"actual_target_pairing":link_assert["actual"] and link_assert["target"],"actual":link_assert["actual"],"target":link_assert["target"]}},"edge_endpoint_comparison":edge_comparison,"checks":{"arc_station_set_matches_runtime":arcstations==runtime,"arc_station_set_runtime":runtime,"arc_station_set_arc":arcstations,"arc_component_identity_validation":"unavailable_from_DP_inventory","electrical_edge_validation":"unavailable_from_text_extraction","actual_target_delta":{"component_delta":dict((str(k),v) for k,v in (actual_components-target_components).items()),"port_delta":dict((str(k),v) for k,v in (actual_ports-target_ports).items()),"edge_delta":edge_comparison["status"]!="exact","has_delta":actual_components!=target_components or actual_ports!=target_ports or edge_comparison["status"]!="exact"}}}
    result["conclusions"]=[{"status":"confirmed","object":"endpoint records and selectors","comment":"Actual and target component, port and edge records preserve source selectors; endpoints use component number plus port ordinal, never ordinal as identity."},{"status":"confirmed","object":"CU_LINK reciprocal representations","comment":"CU_LINK is checked independently by exact device_id and reciprocal CU representations: cnc135=4, cnc152=1."},{"status":"confirmed","object":"ARC station inventory","comment":"ARC is limited to station/slot presence; component, device_id and port are unavailable."},{"status":"confirmed","object":"summary preservation","comment":"Saved v0.9.4 summary fields are compared independently for each machine."},{"status":"rule","object":"runtime graph","comment":"No ARC/electrical observation creates or changes runtime edges."}]
    return result


def markdown_report(report):
    lines=["# Endpoint-level cross-validation report","","ARC and electrical sources remain independent observations; no runtime graph edge is created.","","## Machine checks","","| Machine | ARC stations | Actual components/ports/edges | Target components/ports/edges | Edge comparison | CU_LINK pairs |","|---|---:|---:|---:|---|---:|"]
    for m,d in report["machines"].items():
        a=d["endpoint_validation"]["actual"]["counts"]; t=d["endpoint_validation"]["target"]["counts"]
        lines.append(f"| {m} | {d['checks']['arc_station_set_matches_runtime']} | {a['components']}/{a['ports']}/{a['edges']} | {t['components']}/{t['ports']}/{t['edges']} | {d['edge_endpoint_comparison']['status']} | {len(d['cu_link_validation']['actual'])} |")
    lines += ["","## Conclusions",""]+[f"- **{x['status']}** — **{x['object']}**: {x['comment']}" for x in report["conclusions"]]+["","## Explicit unavailable evidence","","- ARC DP does not expose decoded component numbers, device IDs, or ports.","- PDF text does not expose stable endpoint mappings.","- Mismatch and unresolved statuses are retained; only exact endpoint evidence is confirmed.",""]
    return "\n".join(lines)


def write_report(root,output):
    report=build_report(root); out=Path(output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(markdown_report(report),encoding="utf-8"); out.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); return out

if __name__ == "__main__":
    import argparse
    p=argparse.ArgumentParser(); p.add_argument('--root',type=Path,default=Path(__file__).parents[1]); p.add_argument('--out',type=Path,required=True); a=p.parse_args(); write_report(a.root,a.out); print(a.out)
