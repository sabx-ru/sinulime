from __future__ import annotations
from typing import Any, Mapping
from .dto import success, error, METHODS
from .validation import validate_request, validate_response, ValidationError, validate_event, validate_evidence
from .errors import ApplicationError, NotFound, ResyncRequired, NotComparable
from .cursors import make_cursor, read_cursor
from topology100.reconcile import validate_not_comparable_reason

class OfflineApplicationService:
    def __init__(self, *, snapshots=None, evidence=None, events=None, reconciler=None, coordinator=None, installation_id="offline", schema_version="api-v1", retention_generation=0):
        self.snapshots=snapshots; self.evidence=evidence; self.events=events; self.reconciler=reconciler; self.coordinator=coordinator; self.installation_id=installation_id; self.schema_version=schema_version; self.retention_generation=retention_generation

    def publish(self, publication):
        """Offline publication boundary; acquisition remains separate from topology."""
        if self.coordinator is None: raise RuntimeError("publication coordinator unavailable")
        return self.coordinator.publish(publication)
    def handle(self, request: Mapping[str, Any]):
        notification="id" not in request; request_id=request.get("id")
        try:
            validate_request(request); method=request.get("method")
            if method not in METHODS: return None if notification else error(request_id,"METHOD_NOT_FOUND","method not found",{})
            p=request["params"]
            if method=="capabilities.get": result=self._envelope(method,{"protocol_version":"2.0","schema_version":self.schema_version,"methods":list(METHODS),"live_acquisition":False})
            elif method=="health.get": result=self._envelope(method,{"status":"ready"})
            elif method=="snapshot.get": result=self._envelope(method,{"snapshot":self._get(self._committed_store(self.snapshots),p["snapshot_id"])})
            elif method=="evidence.get":
                value=self._get(self._committed_store(self.evidence),p["evidence_id"]); validate_evidence(value); result=self._envelope(method,{"evidence":value})
            elif method=="snapshot.list": result=self._page(method,self._list(self.snapshots,p),False,p)
            elif method=="event.list": result=self._page(method,self._list_events(p),True,p)
            elif method=="topology.query":
                snap=self._get(self._committed_store(self.snapshots),p["snapshot_id"]); items=list(snap.get("items",snap.get("relations",[]))); result=self._page(method,{"items":items},False,p)
            elif method=="topology.reconcile":
                actual_id=p["actual_snapshot_id"]
                target_id=p["target_snapshot_id"]
                if actual_id == target_id:
                    raise NotComparable("actual and target snapshots must be distinct", {
                        "reason": "identity_mismatch",
                        "actual_snapshot_id": actual_id,
                        "target_snapshot_id": target_id,
                    })
                a=self._get(self._committed_store(self.snapshots),actual_id); t=self._get(self._committed_store(self.snapshots),target_id)
                actual_representation = (a.get("representation"), a.get("role"))
                target_representation = (t.get("representation"), t.get("role"))
                if (not all(actual_representation) or
                        not all(target_representation) or
                        actual_representation != target_representation):
                    raise NotComparable("actual and target representations/roles differ", {
                        "reason": "representation_mismatch",
                        "actual_snapshot_id": actual_id,
                        "target_snapshot_id": target_id,
                    })
                if (a.get("completeness") == "incomplete" or
                        t.get("completeness") == "incomplete" or
                        a.get("availability") == "unavailable" or
                        t.get("availability") == "unavailable"):
                    raise NotComparable("actual and target snapshots are incomplete", {
                        "reason": "incomplete_snapshot",
                        "actual_snapshot_id": actual_id,
                        "target_snapshot_id": target_id,
                    })
                if (a.get("comparison_supported") is False or
                        t.get("comparison_supported") is False):
                    raise NotComparable("comparison is unsupported for these snapshots", {
                        "reason": "unsupported_comparison",
                        "actual_snapshot_id": actual_id,
                        "target_snapshot_id": target_id,
                    })
                reconciliation = self.reconciler(a,t) if self.reconciler else {"status":"not_comparable","items":[]}
                if reconciliation.get("status") == "not_comparable" and reconciliation.get("reason") is not None:
                    reason = validate_not_comparable_reason(reconciliation["reason"])
                    raise NotComparable("comparison is not defined for these snapshots", {
                        "reason": reason,
                        "actual_snapshot_id": actual_id,
                        "target_snapshot_id": target_id,
                    })
                result=self._envelope(method,{"reconciliation":reconciliation})
            else: raise ApplicationError("method not found")
            response=None if notification else success(request_id,result)
            if response is not None: validate_response(response,method)
        except ValidationError as exc: response=None if notification else error(request_id,"INVALID_REQUEST",str(exc),{"violations":exc.violations})
        except ResyncRequired as exc:
            data=dict(exc.data); data["authoritative_snapshot_ids"]=self._snapshot_ids(); data["earliest_retained_offset"]=self._earliest()
            response=None if notification else error(request_id,exc.code,exc.message,data)
        except (NotFound,ApplicationError) as exc: response=None if notification else error(request_id,exc.code,exc.message,exc.data)
        except (KeyError,IndexError) as exc:
            data={"earliest_retained_offset":self._earliest(),"requested_from_event_id":request.get("params",{}).get("from_event_id"),"requested_from_offset":request.get("params",{}).get("from_offset"),"authoritative_snapshot_ids":self._snapshot_ids(),"reason":"replay_start_unavailable"}
            response=None if notification else error(request_id,"RESYNC_REQUIRED","replay start is no longer retained",data)
        except ValueError: response=None if notification else error(request_id,"STORAGE_UNAVAILABLE","stored data failed schema validation",{})
        except Exception: response=None if notification else error(request_id,"INTERNAL_ERROR","internal error",{})
        return response
    def _envelope(self,method,values): return {"contract_version":"api-v1","method":method,**values}
    def _cursor_context(self, method, params, event):
        filters=dict(params.get("filters",{}))
        if event:
            filters.update({k:params[k] for k in ("from_event_id","from_offset") if k in params})
        return dict(method=method, filters=filters, consistency="event_log" if event else "snapshot", installation=self.installation_id, schema=self.schema_version, retention=self.retention_generation)
    def _page(self,method,value,event=False,params=None):
        value=dict(value or {}); value.setdefault("items",[]); value.setdefault("has_more",False)
        raw_next=value.get("next_cursor"); value["next_cursor"] = None
        value.setdefault("consistency","event_log" if event else "snapshot"); value["method"]=method; value["contract_version"]="api-v1"
        if raw_next is not None:
            try:
                position=int(raw_next)
                if isinstance(raw_next, bool) or position < 0: raise ValueError
            except (TypeError, ValueError) as exc: raise ResyncRequired("stored continuation cursor is invalid", {"reason":"cursor_mismatch"}) from exc
            ctx=self._cursor_context(method,params or {},event); value["next_cursor"]=make_cursor(position=position,**ctx)
        if event: value.setdefault("replay",{"mode":"current","from_event_id":None,"from_offset":None,"next_offset":0,"earliest_retained_offset":self._earliest()})
        return value
    @staticmethod
    def _get(store,key):
        if store is None: raise NotFound("store unavailable")
        try: value=store.get(key)
        except KeyError as exc: raise NotFound("resource not found") from exc
        if value is None: raise NotFound("resource not found")
        return value
    def _committed_store(self, store):
        if self.coordinator is None or self.coordinator.current is None:
            return store
        if store is self.snapshots:
            return _CommittedCollection([self.coordinator.current.snapshot], "snapshot_id")
        if store is self.evidence:
            return _CommittedCollection(self.coordinator.current.evidence, "evidence_id")
        if store is self.events:
            return _CommittedCollection(self.coordinator.current.events, "event_id")
        return store
    def _list(self,store,params):
        if store is None: raise NotFound("store unavailable")
        store = self._committed_store(store)
        cursor=params.get("cursor")
        if cursor is not None: cursor=read_cursor(cursor,"snapshot.list",dict(params.get("filters",{})),consistency="snapshot",installation=self.installation_id,schema=self.schema_version,retention=self.retention_generation)
        return store.list(params,cursor,params.get("limit",100))
    def _list_events(self,p):
        if self.events is None: raise NotFound("store unavailable")
        event_store = self._committed_store(self.events)
        cursor=p.get("cursor"); filters=dict(p.get("filters",{})); filters.update({k:p[k] for k in ("from_event_id","from_offset") if k in p})
        if cursor is not None: cursor=read_cursor(cursor,"event.list",filters,consistency="event_log",installation=self.installation_id,schema=self.schema_version,retention=self.retention_generation)
        q=dict(p); return event_store.list(q,cursor,p.get("limit",100))
    def _earliest(self): return self.events.earliest_offset() if self.events is not None and hasattr(self.events,"earliest_offset") else 0
    def _snapshot_ids(self):
        if self.coordinator is not None and self.coordinator.current is not None:
            item=self.coordinator.current.snapshot
            return [item.get("snapshot_id", item.get("id"))]
        if self.snapshots is None: return []
        try: return [x.get("id") for x in self.snapshots.list({},None,1000).get("items",[]) if x.get("id")]
        except Exception: return []

class _CommittedCollection:
    def __init__(self, items, key):
        self._items = list(items)
        self._key = key
    def get(self, value):
        for item in self._items:
            if item.get(self._key) == value or item.get("id") == value:
                return item
        raise KeyError(value)
    def list(self, query=None, cursor=None, limit=100):
        start = int(cursor) if cursor is not None else 0
        page = self._items[start:start + limit]
        end = start + len(page)
        return {"items": page, "has_more": end < len(self._items),
                "next_cursor": str(end) if end < len(self._items) else None}
