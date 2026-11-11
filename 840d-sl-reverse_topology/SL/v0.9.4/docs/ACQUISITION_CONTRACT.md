# Acquisition Contract

**Status:** read-only interface design; no implementation in Stage 1.

## Boundary

Acquisition returns immutable raw observations and journal metadata. It does not decode topology, assign domain IDs, infer connections, reconcile Actual/Target, persist state, or expose a network API. It has no generic write primitive: WriteVar, Download, motion, PLC writes, and drive-control writes are rejected.

```text
AcquisitionSource.open(request) -> AcquisitionSession
AcquisitionSession.read(item) -> RawObservation
AcquisitionSession.read_batch(items) -> list[RawObservation]
AcquisitionSession.health() -> HealthObservation
AcquisitionSession.close() -> None
CaptureReader.iter_observations(artifact_id) -> iterator[RawObservation]
```

`AcquisitionRequest` contains installation/station identity, an allowlisted item plan, timeout, bounded retry/reconnect policy, cancellation token, and `mode=live|replay`. Replay takes an artifact ID and must not create a network session. Actual and Target plans are separate and preserve their parameter provenance.

`ReadItem` preserves exact `{area, block, unit, param, index}`. `RawObservation` contains request reference, artifact ID, exact source reference, value or explicit absence, status (`ok`, `missing`, `invalid`, `timeout`, `transport_error`, `cancelled`), attempt, UTC time, adapter/version, and SHA-256 when available. No absent value becomes zero, an empty string, or a guessed address.

## Evidence handoff and sparse indices

Every observation that may support a relationship receives a unique `evidence_id` at the evidence boundary and retains the exact raw artifact reference, endpoint identity (when known), original source index, and decoder status. For sparse sensor arrays, the original source index is authoritative and must be preserved through filtering and parallel encoder lookup. Missing, duplicated, or ambiguous source indices produce `ambiguous_mapping` and unresolved downstream relations; enumeration position is never substituted.

The decoder emits typed values/TLV records and failures. The resolver consumes those records plus evidence and can emit only evidence-gated confirmed relations, reference-only relations, or unresolved records. State Manager validates artifact hashes and publishes immutable Actual/Target payloads.

## Safety and compatibility

Only allowlisted read plans can be submitted. Timeouts/retries are bounded and reconnects are journaled. A changed station identity fails the session or marks observations unresolved according to policy. Partial captures are valid only when completeness and failure reasons are recorded. Legacy journals and SDB binaries can be read by an adapter, but their generic evidence fields are non-conforming until migrated.

Measured fixture examples are cnc135 5/19/58/4 and cnc152 2/6/13/1 (CU/axes/edges/CU_LINK); they are not defaults. Stage 1 does not run a live CNC or alter topology runtime code.

Structured errors include `ITEM_UNSUPPORTED`, `TIMEOUT`, `RETRY_EXHAUSTED`, `RECONNECT_FAILED`, `IDENTITY_CHANGED`, `INVALID_RESPONSE`, `CAPTURE_CORRUPT`, `CANCELLED`, and `READ_ONLY_POLICY`, with request/source refs, attempts, and retryability; secrets are excluded.
