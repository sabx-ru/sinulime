# Stage 3 design gate — API and persistence contracts

**Status:** B3 additive topology100 envelope identity projection implemented; broader Stage 3 implementation readiness remains blocked by explicit gates.

## Scope and non-goals

This gate specifies a transport-neutral, read-only application boundary. It does not implement HTTP, WebSocket, acquisition, NiceGUI, a database, or live monitoring. PDF/electrical-drawing/ARC comparison remain external analysis. A deployment adapter may expose these contracts later; it may not bypass domain validation or mutate state directly.

The dependency direction is `adapter -> application ports -> state/evidence/resolution -> domain`; acquisition and decoding are inputs, and persistence is behind ports. Physical devices, logical objects, channels, ports, and connections remain distinct. `ActualSnapshot` and `TargetSnapshot` are separate representations, even when equal.

## B1 — conformance and validator boundary

`docs/schema/api-v1.schema.json` is the normative wire schema. `docs/schema/topology-v1.schema.json` is the normative snapshot/evidence payload schema. A **contract validator** sits at the application boundary, before persistence/publication and before any response is emitted. It validates JSON shape, required fields, enums, additional properties, request method/params, response envelopes, and error/event envelopes. A **domain/evidence validator** then validates topology invariants: endpoint-kind selectors, Actual/Target separation, evidence references, and the confirmed-relation gate. Schema validation alone never confirms a relationship.

The validator is pure, deterministic, side-effect free, and returns structured violations with JSON pointer, code, and message. Invalid input is rejected as `INVALID_REQUEST`; invalid internal publication is rejected before atomic commit as `INTERNAL_ERROR` and must not become visible. Conforming evidence requires the fields and rules in `docs/schema/evidence-v1-conformance.md`.

## B2 — identity

For a stable identity, compute UUIDv5 with namespace `uuid5(NAMESPACE_URL, "sinumerik-core")` and UTF-8 name:

`v1|<installation_id>|<kind>|<canonical-source-json>`

`canonical-source-json` is RFC 8785-style canonical JSON: object keys lexicographically sorted recursively, arrays preserved, UTF-8, no insignificant whitespace, exact field names, and numbers encoded as JSON numbers (not strings). `installation_id`, `kind`, and source identity are required and are not normalized beyond their contract values. The schema version is the literal `v1` in the name. Stable IDs are immutable.

When source identity is missing, duplicated, or ambiguous, compute a **provisional** UUIDv5 using name:

`v1|<installation_id>|<snapshot_id>|provisional|<kind>|<canonical-source-observation-json>`

Set `identity_status=provisional`, retain the observation and evidence, and do not confirm dependent topology. Promotion requires an explicit mapping retaining old and new IDs plus evidence; address order or list position is never sufficient.

**B3 implementation status:** The additive `evidence.v1.json` projection uses the published B2 stable/provisional ID functions, never the legacy `identity_id` wrapper. The current legacy axis/component/drive records do not define kind-specific canonical source identity contracts, including duplicate/ambiguity semantics. They therefore remain provisional, scoped by `installation_id` and `snapshot_id`; a provisional endpoint cannot support a confirmed relation. Legacy `evidence.json`, `summary.json`, and captures are unchanged. `write_evidence` accepts an optional installation scope for the additive envelope. This does not change `identity_id` or claim broader Stage 3 readiness.

## B3 — stores, atomic publication, revisions, retention, restart

Ports are minimal and transport/database independent. All IDs and cursors are opaque strings.

```text
SnapshotStore
  get(snapshot_id) -> Snapshot | NotFound
  list(query: SnapshotQuery, cursor: Cursor|null, limit: int) -> Page[SnapshotSummary]
  prepare_publish(snapshot, expected_revision: int|null) -> PreparedPublication

EvidenceStore
  get(evidence_id) -> Evidence | NotFound
  put_batch(evidence[]) -> void                 # idempotent by evidence_id/content hash

EventStore
  append_batch(events[], revision) -> EventRange
  list(query, from_offset|from_event_id|cursor) -> EventPage
  earliest_offset() -> int
  retain_through(offset) -> void

JobStore
  get(job_id) -> Job | NotFound
  put(job) -> void
  list(query, cursor, limit) -> Page[JobSummary]

RawArtifactStore
  get(artifact_id) -> ArtifactMetadata | NotFound
  open(artifact_id) -> ReadOnlyByteStream
  put(metadata, bytes) -> ArtifactRef          # content-addressed/idempotent
```

`PreparedPublication` is committed by the application transaction coordinator, not by an individual store. One publication atomically writes evidence, immutable snapshot, revision allocation, and corresponding events; readers see either the prior committed revision or the complete new revision, never a partial set. Revisions are monotonically increasing per `installation_id` and never reused. A restart reloads the last committed revision and event offset, replays no side effects, and resumes from the durable retention boundary. Retention is bounded and documented; deletion never changes an existing snapshot or event ID. If an event needed for replay is gone, return `RESYNC_REQUIRED` with an authoritative snapshot ID.

## B4 — artifact resolver and path security

The default input is an opaque `artifact_id`; callers cannot supply a filesystem path or URL. An optional deployment adapter may resolve a local path only when explicitly enabled. It must reject before opening: NUL bytes, absolute paths outside the configured root, `..` traversal after canonicalization, symlinks escaping the allowlist (and symlink policy violations), network URLs/schemes, non-regular files, unsupported format, and files over the configured byte limit. It canonicalizes with the platform real-path operation, authorizes the canonical path under an allowlisted root, reads bounded bytes, computes SHA-256, and records canonical relative path, size, media/format, and hash. TOCTOU-sensitive deployments must open safely and verify the opened file remains a regular authorized file. Artifact IDs remain opaque and are the only production-core reference.

## B5 — JSON-RPC v1 surface

JSON-RPC 2.0 is the application message model; transport is deliberately unspecified. Request `jsonrpc` is exactly `2.0`, `id` is echoed exactly for non-notifications, and `method` is one of: `capabilities.get`, `snapshot.list`, `snapshot.get`, `topology.query`, `topology.reconcile`, `evidence.get`, `event.list`, `health.get`. No job or live-acquisition method exists in v1. Unknown methods are `METHOD_NOT_FOUND`. Notifications have no response.

Every success is `{jsonrpc,id,result}` and every failure is `{jsonrpc,id,error:{code,message,data}}`; error `code` is a stable string. Required codes include `INVALID_REQUEST`, `METHOD_NOT_FOUND`, `NOT_FOUND`, `INVALID_SOURCE`, `NOT_COMPARABLE`, `REMOTE_BIND_REJECTED`, `RESYNC_REQUIRED`, `UNRESOLVED_TOPOLOGY`, `STORAGE_UNAVAILABLE`, `MESSAGE_TOO_LARGE`, and `INTERNAL_ERROR`. `NOT_COMPARABLE` is a valid `topology.reconcile` request outcome when Actual/Target comparison is undefined or unavailable under the domain rules; its data carries a constrained comparison reason. `data` contains no secrets.

Methods are query-only. `snapshot.list` accepts bounded `limit`, filters, and opaque `cursor`; `snapshot.get` requires `snapshot_id`; `topology.query` requires `snapshot_id` and optional endpoint/kind filters; `topology.reconcile` requires `actual_snapshot_id` and `target_snapshot_id`; `evidence.get` requires `evidence_id`; `event.list` accepts filters, bounded `limit`, opaque `cursor`, and at most one of `from_event_id`/`from_offset`; `capabilities.get` and `health.get` take an empty object. Exact request/response shapes are in `api-v1.schema.json`.

## B6 — cursors, replay, authoritative resync

Cursors and replay tokens are opaque, versioned server values. They are bound to method, canonical filter, consistency token, installation scope, schema version, and retention generation; a client must not decode or construct them. `from_event_id` and `from_offset` are mutually exclusive; both supplied is `INVALID_REQUEST`. Each is exclusive: the named event/offset is not replayed. Event ordering is by durable offset, with immutable `event_id` for deduplication.

An expired/unknown/mismatched cursor, expired starting point, or a subscription gap returns `RESYNC_REQUIRED` and data `{earliest_retained_offset, requested_from_event_id, requested_from_offset, authoritative_snapshot_ids, reason}`. The client fetches an authoritative snapshot, discards/reconciles local derived state, then requests a fresh cursor. Events are hints; snapshots are authoritative.

## B7 — bind policy and deployment adapter

Before listen, a deployment adapter validates the configured bind address. Default policy permits loopback only (`127.0.0.0/8`, `::1`); a non-loopback bind is rejected before socket listen and audited as `REMOTE_BIND_REJECTED`. No request parameter can override this. Any future remote deployment requires explicit external authentication/authorization, origin policy, audit, and limits; it is outside this contract. The core sees only an abstract request/response adapter.

## B8 — bounded subscriptions and deferred transport

Subscriptions are not a v1 method and no WebSocket protocol is defined here. A future adapter may use a bounded queue with a documented maximum. Overflow must not grow memory: emit a gap/`RESYNC_REQUIRED`, close or pause the subscription, and require an authoritative snapshot. Health/progress notifications may be coalesced; snapshot/topology events may not be silently dropped. Live acquisition, WebSocket framing/handshake, authentication, and reconnect transport are explicitly deferred.

## Acceptance matrix and contract tests

| Blocker | Normative artifact/decision | Required test before implementation acceptance |
|---|---|---|
| B1 | validator boundary and evidence gate | invalid envelope/schema/evidence rejected before publication; valid evidence accepted |
| B2 | exact stable/provisional UUIDv5 algorithm | same canonical input is identical; installation/schema/kind changes differ; provisional scope differs; no promotion by ordering |
| B3 | five store ports, atomic commit, revision/retention/restart | crash before/after commit exposes one revision only; restart preserves revision/offset; retention produces resync |
| B4 | opaque artifact default and canonical allowlist | reject NUL, traversal, escaping symlink, URL, non-regular, oversize; record size/hash/path |
| B5 | query-only JSON-RPC surface | golden request/response/error fixtures; jobs/live methods rejected |
| B6 | opaque binding and exclusive replay starts | both from fields rejected; exclusivity/order verified; stale token returns authoritative resync data |
| B7 | pre-listen loopback policy | non-loopback never listens and emits `REMOTE_BIND_REJECTED` |
| B8 | bounded overflow semantics and deferral | bounded queue overflows into gap/resync without unbounded growth; no transport implementation required |

### Explicit implementation gates carried from earlier stages

| Gate | Status | Required before Stage 3 implementation-ready |
|---|---|---|
| Sparse sensor source index | **BLOCKED** | Preserve original sparse indices through filtering/parallel lookup; missing, duplicate, or ambiguous indices remain unresolved and covered by a contract test. |
| Published identity algorithm | **BLOCKED** | Align `topology100/identity.py` with B2; add deterministic stable/provisional vectors and promotion tests. |

The schema-derived checks for this design gate must reject method/params mismatches, method/result mismatches, both evidence observation forms, null observed values, missing endpoint identity status, incomplete artifact metadata, and incomplete `RESYNC_REQUIRED` data. These are structural checks only; semantic evidence and relationship confirmation remain domain-validator responsibilities.

No production code, runtime topology code, captures, or runs are changed by this design gate.
