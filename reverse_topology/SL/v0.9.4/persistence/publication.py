from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json, os, tempfile
from application.validation import validate_event, validate_evidence, ValidationError
from topology100.contracts import validate_envelope

@dataclass(frozen=True)
class Publication:
    revision: int; snapshot: dict; evidence: tuple[dict, ...] = (); events: tuple[dict, ...] = ()

class PublicationCoordinator:
    """Coordinates a durable manifest with the three offline collection stores.

    Artifacts are staged in a revision directory and the manifest is replaced
    last.  Readers use ``current`` only, so a crash before the marker replace
    leaves the previous complete revision visible.
    """
    def __init__(self, path=None, *, snapshots=None, evidence=None, events=None):
        self.path=Path(path) if path else None
        self.snapshots=snapshots; self.evidence=evidence; self.events=events
        self._publication=self._load()
        self._bind_stores()

    def _bind_stores(self):
        for store, filename in ((self.snapshots, "snapshots.json"), (self.evidence, "evidence.json"), (self.events, "events.json")):
            if store is not None:
                store.generation_manifest = str(self.path) if self.path else None
                store.generation_file = filename

    def _load(self):
        if not self.path or not self.path.exists(): return None
        try:
            value=json.loads(self.path.read_text(encoding="utf-8"))
            if set(value) == {"generation", "revision"}:
                manifest_revision = value["revision"]
                if not isinstance(manifest_revision, int) or isinstance(manifest_revision, bool) or manifest_revision < 0:
                    raise ValueError("invalid manifest revision")
                expected = self.path.name + f".revision-{manifest_revision}"
                pointer = value["generation"]
                if not isinstance(pointer, str) or pointer != expected or Path(pointer).is_absolute() or Path(pointer).name != pointer:
                    raise ValueError("invalid generation pointer")
                generation = self.path.parent / pointer
                value = json.loads((generation / "publication.json").read_text(encoding="utf-8"))
                if value.get("revision") != manifest_revision:
                    raise ValueError("generation revision mismatch")
                for filename in ("snapshots.json", "evidence.json", "events.json"):
                    if not (generation / filename).exists(): raise ValueError("generation incomplete")
            if not isinstance(value,dict) or set(value) != {"revision","snapshot","evidence","events"}: raise ValueError
            if not isinstance(value["revision"],int) or isinstance(value["revision"], bool) or value["revision"] < 0 or not isinstance(value["snapshot"],dict) or not isinstance(value["evidence"],list) or not isinstance(value["events"],list): raise ValueError
            validate_envelope(value["snapshot"])
            for evidence in value["evidence"]:
                if not isinstance(evidence, dict): raise ValueError("invalid evidence record")
                validate_evidence(evidence)
            for event in value["events"]: validate_event(event)
            return Publication(value["revision"],value["snapshot"],tuple(value["evidence"]),tuple(value["events"]))
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError, ValidationError) as exc:
            raise RuntimeError("publication state is corrupted or incomplete") from exc

    @staticmethod
    def _validate(publication):
        if not isinstance(publication,Publication): raise TypeError("publication required")
        if not isinstance(publication.revision, int) or isinstance(publication.revision, bool) or publication.revision < 0: raise ValueError("invalid revision")
        validate_envelope(publication.snapshot)
        for evidence in publication.evidence: validate_evidence(evidence)
        for event in publication.events: validate_event(event)

    def prepare(self, publication):
        """Validate and stage artifacts; no reader-visible state changes."""
        self._validate(publication)
        if self._publication and publication.revision <= self._publication.revision: raise ValueError("revision must increase")
        if not self.path: return publication
        stage=self.path.parent / (self.path.name + f".revision-{publication.revision}.stage")
        if stage.exists():
            import shutil
            shutil.rmtree(stage)
        stage.mkdir(parents=True, exist_ok=True)
        value={"revision":publication.revision,"snapshot":publication.snapshot,"evidence":list(publication.evidence),"events":list(publication.events)}
        payload=json.dumps(value, sort_keys=True, separators=(",",":"))
        (stage / "publication.json").write_text(payload, encoding="utf-8")
        (stage / "snapshots.json").write_text(json.dumps([publication.snapshot], sort_keys=True, separators=(",",":")), encoding="utf-8")
        (stage / "evidence.json").write_text(json.dumps(list(publication.evidence), sort_keys=True, separators=(",",":")), encoding="utf-8")
        (stage / "events.json").write_text(json.dumps(list(publication.events), sort_keys=True, separators=(",",":")), encoding="utf-8")
        for artifact in (stage / "publication.json", stage / "snapshots.json", stage / "evidence.json", stage / "events.json"):
            with artifact.open("rb") as f: os.fsync(f.fileno())
        # Rename the complete staged directory before changing the pointer.
        generation=self.path.parent / (self.path.name + f".revision-{publication.revision}")
        if generation.exists():
            import shutil
            shutil.rmtree(generation)
        os.replace(stage, generation)
        return publication

    def commit(self, publication):
        self.prepare(publication)
        generation=self.path.name + f".revision-{publication.revision}"
        value={"generation":generation,"revision":publication.revision}
        if self.path:
            self.path.parent.mkdir(parents=True,exist_ok=True); fd,tmp=tempfile.mkstemp(dir=self.path.parent,prefix=self.path.name+".")
            try:
                with os.fdopen(fd,"w",encoding="utf-8") as f: json.dump(value,f,sort_keys=True,separators=(",",":")); f.flush(); os.fsync(f.fileno())
                os.replace(tmp,self.path)
                try:
                    dfd=os.open(self.path.parent, os.O_DIRECTORY); os.fsync(dfd); os.close(dfd)
                except (AttributeError,OSError): pass
            finally:
                if os.path.exists(tmp): os.unlink(tmp)
        self._publication=publication; return publication

    def publish(self, publication):
        """Stage one complete generation and atomically publish its pointer."""
        return self.commit(publication)

    @property
    def current(self): return self._publication

    def committed_snapshot(self, snapshot_id):
        if self._publication is None: raise KeyError(snapshot_id)
        snapshot=self._publication.snapshot
        if snapshot.get("snapshot_id") != snapshot_id and snapshot.get("id") != snapshot_id: raise KeyError(snapshot_id)
        return snapshot

    def committed_evidence(self, evidence_id):
        if self._publication is None: raise KeyError(evidence_id)
        for item in self._publication.evidence:
            if item.get("evidence_id") == evidence_id: return item
        raise KeyError(evidence_id)

