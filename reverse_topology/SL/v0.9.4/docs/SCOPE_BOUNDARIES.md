# Stage 0 — Scope boundaries

## In scope

- Audit of the existing SINUMERIK/SINAMICS read-only acquisition and offline topology processing.
- Reproducible replay/rebuild from saved `runs/cnc135` and `runs/cnc152` data.
- Explicit handling and reporting of missing values, partial reads, incomplete TLV, ambiguous mappings, retries, timeouts and reconnections as unresolved/incomplete rather than fabricated success.
- Internal Actual/Target/consistency checks, including equality/inequality of edge sets and reciprocal port validation.
- Documentation of contracts, dependencies, baseline facts and known issues.

## Explicitly excluded from production core

- PDF parsing, `pdftotext`, electrical drawing parsing or electrical endpoint inference.
- ARC parsing/creation and any ARC-derived runtime edge creation.
- Any write operation to CNC equipment: no WriteVar, Download, motion command, PLC write or drive-control write.
- Live CNC testing in Stage 0.
- Moving or integrating `topology100/cross_validate.py` in Stage 0.
- Deleting, rewriting or relocating captures, runs or reference data.
- Fixing production bugs or redesigning acquisition behavior in this documentation-only stage.

ARC/PDF/electrical material may be considered later as independent corroboration, with explicit unavailable/unresolved results. It must never manufacture a runtime connection or replace CNC evidence.

## Safety and architecture boundary

Acquisition remains read-only and topology processing remains independent of acquisition transport. Offline replay is the acceptance path for the existing snapshots. Future monitoring/UI layers must consume model/state contracts and must not connect directly to CNC or issue writes.

## Acceptance boundary for Stage 0

Stage 0 is complete when the four audit documents exist, measured baseline facts and limitations are recorded, captures remain intact, and available offline tests/checks pass. It does not claim live connectivity, git history, ARC/PDF correctness, or full monitoring-system readiness.
