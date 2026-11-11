"""Installation and capture provenance value objects.

Installation identity is resolved only from explicitly trusted, scoped sources.
Capture host/process metadata is provenance and never participates in installation
identity resolution.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


_TRUSTED_KINDS = {"trusted_configuration", "deployment_metadata", "machine_id", "plant_id", "source_local_id"}


@dataclass(frozen=True)
class InstallationIdentity:
    identifier: str | None
    source_kind: str | None = None
    source_field: str | None = None
    scope: str | None = None
    stability: str | None = None
    confidence: str = "unknown"
    evidence_ref: str | None = None
    status: str = "unknown"

    def __post_init__(self) -> None:
        if self.status not in {"unknown", "confirmed", "conflict", "provisional"}:
            raise ValueError("invalid installation identity status")
        if self.status == "confirmed":
            fields = (self.identifier, self.source_kind, self.source_field,
                      self.scope, self.stability, self.evidence_ref)
            if not all(isinstance(value, str) and value for value in fields):
                raise ValueError("confirmed installation identity requires provenance")
            if self.source_kind not in _TRUSTED_KINDS:
                raise ValueError("confirmed installation identity requires trusted source")
            if self.confidence not in {"high", "confirmed"}:
                raise ValueError("confirmed installation identity requires confidence")
        elif self.status == "unknown":
            if any(value is not None for value in (
                    self.identifier, self.source_kind, self.source_field,
                    self.scope, self.stability, self.evidence_ref)):
                raise ValueError("unknown installation identity cannot carry identity data")
            if self.confidence != "unknown":
                raise ValueError("unknown installation identity requires unknown confidence")
        elif self.status == "conflict":
            if (self.identifier is not None or self.source_kind != "conflict" or
                    self.source_field != "installation_id" or self.scope != "conflict" or
                    self.stability is not None or not self.evidence_ref or
                    self.confidence != "unknown"):
                raise ValueError("conflict installation identity requires explicit provenance")
        elif self.status == "provisional":
            if self.confidence not in {"low", "provisional", "unknown"}:
                raise ValueError("provisional installation identity cannot be confirmed")
            if self.source_kind in _TRUSTED_KINDS:
                raise ValueError("provisional installation identity cannot use trusted source")

    @classmethod
    def unknown(cls) -> "InstallationIdentity":
        return cls(None)

    def to_dict(self) -> dict[str, Any]:
        return {"identifier": self.identifier, "source_kind": self.source_kind,
                "source_field": self.source_field, "scope": self.scope,
                "stability": self.stability,
                "confidence": self.confidence, "evidence_ref": self.evidence_ref,
                "status": self.status}


@dataclass(frozen=True)
class CaptureHostIdentity:
    host_id: str | None = None
    process_id: str | None = None
    captured_at: str | None = None
    adapter: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"host_id": self.host_id, "process_id": self.process_id,
                "captured_at": self.captured_at, "adapter": self.adapter}


def resolve_installation_identity(sources: Sequence[Mapping[str, Any]] | None = None) -> InstallationIdentity:
    """Resolve explicit trusted assignments; host/process data is intentionally ignored.

    Each source must provide identifier, kind, field, scope, confidence and evidence.
    Conflicting trusted assignments are surfaced with their provenance.
    """
    candidates: list[InstallationIdentity] = []
    for source in sources or ():
        if not isinstance(source, Mapping):
            continue
        kind = source.get("source_kind")
        identifier = source.get("identifier")
        required = (identifier, source.get("source_field"), source.get("scope"),
                    source.get("stability"), source.get("evidence_ref"))
        if (kind not in _TRUSTED_KINDS or
                not all(isinstance(value, str) and value for value in required)):
            continue
        confidence = source.get("confidence", "high")
        if confidence not in {"high", "confirmed"}:
            continue

        candidates.append(InstallationIdentity(
            identifier=identifier, source_kind=kind, source_field=source["source_field"],
            scope=source["scope"], stability=source.get("stability"),
            confidence=confidence, evidence_ref=source["evidence_ref"],
            status="confirmed"))
    if not candidates:
        return InstallationIdentity.unknown()
    identifiers = {candidate.identifier for candidate in candidates}
    if len(identifiers) > 1:
        refs = ",".join(sorted(str(candidate.evidence_ref) for candidate in candidates))
        return InstallationIdentity(identifier=None, source_kind="conflict",
                                   source_field="installation_id", scope="conflict",
                                   stability=None, confidence="unknown", evidence_ref=refs,
                                   status="conflict")
    first = candidates[0]
    return first


def identity_from_legacy(legacy: Mapping[str, Any]) -> InstallationIdentity:
    """Adapt a legacy installation field as provisional until evidence is supplied."""
    value = legacy.get("installation_id")
    if not isinstance(value, str) or not value:
        return InstallationIdentity.unknown()
    return InstallationIdentity(identifier=value, source_kind="legacy_field",
                                source_field="installation_id", scope="legacy",
                                stability="snapshot", confidence="low",
                                evidence_ref="legacy-envelope", status="provisional")
