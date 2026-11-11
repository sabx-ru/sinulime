from __future__ import annotations
import json, os, tempfile
from pathlib import Path
from typing import Any
from application.validation import validate_event, ValidationError

class JsonFileStore:
    def __init__(self, path): self.path=Path(path)
    def read(self, default=None):
        try: return json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError: return default
    def publish(self, value):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd,tmp=tempfile.mkstemp(dir=self.path.parent, prefix=self.path.name+".")
        try:
            with os.fdopen(fd,"w",encoding="utf-8") as f:
                json.dump(value,f,sort_keys=True,separators=(",",":")); f.flush(); os.fsync(f.fileno())
            os.replace(tmp,self.path)
            try:
                fd=os.open(self.path.parent, os.O_DIRECTORY); os.fsync(fd); os.close(fd)
            except (AttributeError,OSError): pass
        finally:
            if os.path.exists(tmp): os.unlink(tmp)
class ReadOnlyFileStore(JsonFileStore):
    def publish(self, value): raise PermissionError("read-only store")

class FileCollectionStore:
    def __init__(self, path, *, key="id"):
        self.file=JsonFileStore(path); self.key=key
        self.generation_manifest = None
        self.generation_file = None
    def _read_items(self):
        if self.generation_manifest is not None and self.generation_file is not None:
            manifest=JsonFileStore(self.generation_manifest).read(None)
            if not manifest: return []
            pointer=manifest.get("generation")
            revision=manifest.get("revision")
            expected=Path(self.generation_manifest).name + f".revision-{revision}"
            if not isinstance(pointer, str) or pointer != expected or Path(pointer).is_absolute() or Path(pointer).name != pointer:
                raise ValueError("invalid generation pointer")
            target=Path(self.generation_manifest).parent / pointer / self.generation_file
            return JsonFileStore(target).read([])
        return self.file.read([])
    def _items(self):
        items=self._read_items()
        if not isinstance(items,list): raise ValueError("collection store is not an array")
        return items
    def get(self, value):
        for item in self._items():
            if isinstance(item,dict) and self._item_key(item)==value: return item
        raise KeyError(value)
    def _item_key(self, item):
        return item.get(self.key, item.get("id"))
    def list(self, query=None, cursor=None, limit=100):
        if not isinstance(limit,int) or isinstance(limit,bool) or not 1<=limit<=1000: raise ValueError("limit must be 1..1000")
        try: start=int(cursor) if cursor is not None else 0
        except (TypeError,ValueError): raise ValueError("invalid cursor")
        items=self._items()
        if start<0 or start>len(items): raise ValueError("invalid cursor")
        page=items[start:start+limit]; end=start+len(page)
        return {"items":page,"has_more":end<len(items),"next_cursor":str(end) if end<len(items) else None}
    def put(self, item):
        if not isinstance(item,dict) or self._item_key(item) is None: raise ValueError("collection item key required")
        item=dict(item); item.setdefault(self.key, item.get("id"))
        items=[x for x in self._items() if self._item_key(x)!=item[self.key]]; items.append(item); self.file.publish(items)
    def put_batch(self, items):
        items=list(items); current=self._items(); by_key={self._item_key(x):x for x in current}
        for item in items:
            if not isinstance(item,dict) or self._item_key(item) is None: raise ValueError("collection item key required")
            item=dict(item); item.setdefault(self.key, item.get("id"))
            old=by_key.get(item[self.key])
            if old is not None and old != item: raise ValueError("conflicting duplicate")
            by_key[item[self.key]]=dict(item)
        self.file.publish(list(by_key.values()))

class SnapshotStore(FileCollectionStore):
    def __init__(self, path): super().__init__(path, key="snapshot_id")
class EvidenceStore(FileCollectionStore):
    def __init__(self, path): super().__init__(path, key="evidence_id")
class EventStore(FileCollectionStore):
    def __init__(self, path):
        super().__init__(path, key="event_id")
        self._floor_file = JsonFileStore(str(Path(path)) + ".retention")
        self._revision_file = JsonFileStore(str(Path(path)) + ".revision")
        self._txn_file = JsonFileStore(str(Path(path)) + ".txn")
        pending = self._txn_file.read(None)
        if pending is not None:
            if not isinstance(pending, dict) or not isinstance(pending.get("items"), list): raise ValueError("invalid event transaction")
            self.file.publish(pending["items"])
            if "floor" in pending: self._floor_file.publish(pending["floor"])
            if pending.get("revision") is not None: self._revision_file.publish(pending["revision"])
            self._txn_file.publish(None)
        raw_revision = self._revision_file.read(None)
        if raw_revision is not None and (not isinstance(raw_revision, int) or isinstance(raw_revision, bool) or raw_revision < 0):
            raise ValueError("invalid event revision")
        self._last_revision = raw_revision
        try:
            self._retained_floor = int(self._floor_file.read(0) or 0)
        except (TypeError, ValueError):
            raise ValueError("invalid retention floor")
        if self._retained_floor < 0:
            raise ValueError("invalid retention floor")

    def _items(self):
        items=super()._items()
        offsets=[]
        for event in items:
            try: validate_event(event)
            except ValidationError as exc: raise ValueError("invalid stored event") from exc
            offsets.append(event["offset"])
        if offsets != sorted(offsets) or len(offsets) != len(set(offsets)):
            raise ValueError("stored event offsets are not monotonic")
        if any(offset < self._retained_floor for offset in offsets):
            raise ValueError("stored event is below retention floor")
        return items

    def earliest_offset(self):
        items = self._items()
        return max(self._retained_floor, min((x["offset"] for x in items), default=self._retained_floor))

    def append_batch(self, events, revision=None):
        events=list(events)
        if revision is not None and (not isinstance(revision, int) or isinstance(revision, bool) or revision < 0):
            raise ValueError("revision must be a non-negative integer")
        if revision is not None and self._last_revision is not None and revision <= self._last_revision:
            raise ValueError("event revision must increase across batches")
        for event in events:
            try: validate_event(event)
            except ValidationError as exc: raise ValueError("invalid event") from exc
            # Legacy pre-v1 fixtures have no revision field.  Modern events
            # must carry the batch revision and cannot mix revisions.
            if set(event) != {"id", "event_id", "offset"}:
                if revision is None: raise ValueError("revision is required")
                if event["revision"] != revision: raise ValueError("event revision mismatch")
            elif revision is not None:
                raise ValueError("legacy events cannot carry a revision")
            if event["offset"] < self._retained_floor:
                raise ValueError("event offset is below retention floor")
        existing=self._items()
        old_offsets=[event["offset"] for event in existing]
        new_offsets=[event["offset"] for event in events]
        if new_offsets != sorted(new_offsets) or len(new_offsets) != len(set(new_offsets)):
            raise ValueError("event offsets must be strictly increasing")
        if old_offsets and new_offsets and new_offsets[0] <= old_offsets[-1]:
            raise ValueError("event offsets must increase")
        # Journal the complete next state before either data or revision marker.
        next_items={x["event_id"]: x for x in existing}
        next_items.update({x["event_id"]: x for x in events})
        if revision is not None:
            self._txn_file.publish({"items": list(next_items.values()), "revision": revision})
        FileCollectionStore.put_batch(self, events)
        if revision is not None:
            self._revision_file.publish(revision)
            self._txn_file.publish(None)
            self._last_revision = revision
        return events

    def list(self, query=None, cursor=None, limit=100):
        query=query or {}
        if not isinstance(limit,int) or isinstance(limit,bool) or not 1<=limit<=1000: raise ValueError("limit must be 1..1000")
        items=sorted(self._items(),key=lambda x:x["offset"])
        if "from_offset" in query:
            start=int(query["from_offset"])+1
            if start < self.earliest_offset(): raise IndexError("retained event range does not include requested offset")
            items=[x for x in items if x["offset"]>=start]
        elif "from_event_id" in query:
            ids=[i for i,x in enumerate(items) if x["event_id"]==query["from_event_id"]]
            if not ids: raise KeyError(query["from_event_id"])
            items=items[ids[0]+1:]
        if cursor is not None:
            try: start=int(cursor)
            except (TypeError,ValueError): raise ValueError("invalid cursor")
            if start < 0: raise ValueError("invalid cursor")
            # Event cursors are coordinates in the durable log, never indexes
            # into a filtered view. This prevents insertions/retention from
            # replaying or silently skipping records between pages.
            if start < self.earliest_offset(): raise IndexError("event cursor is no longer retained")
            items=[x for x in items if x["offset"] >= start]
        page=items[:limit]; next_pos=(page[-1]["offset"]+1 if page else int(cursor or (items[0]["offset"] if items else 0)))
        return {"items":page,"has_more":len(items)>len(page),"next_cursor":str(next_pos) if len(items)>len(page) else None,
            "replay":{"mode":"from_offset" if "from_offset" in query else "from_event_id" if "from_event_id" in query else "current","from_event_id":query.get("from_event_id"),"from_offset":query.get("from_offset"),"next_offset":(page[-1]["offset"]+1 if page else 0),"earliest_retained_offset":self.earliest_offset()}}
    def put_batch(self, items):
        # There must be no unvalidated write path for the event log.
        return self.append_batch(items)
    def retain_through(self, offset):
        if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
            raise ValueError("retention offset must be a non-negative integer")
        items = super()._items()
        next_floor = max(getattr(self, "_retained_floor", 0), offset + 1)
        new_items=[x for x in items if x["offset"]>offset]
        self._txn_file.publish({"items": new_items, "floor": next_floor})
        self.file.publish(new_items)
        self._floor_file.publish(next_floor)
        self._txn_file.publish(None)
        self._retained_floor = next_floor
class JobStore(FileCollectionStore): pass
class RawArtifactStore(FileCollectionStore): pass
