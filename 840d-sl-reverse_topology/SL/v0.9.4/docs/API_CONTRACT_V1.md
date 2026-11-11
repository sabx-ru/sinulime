# API Contract V1

**Status:** normative design contract; query-only, transport-neutral; no API/WebSocket/live implementation.

## JSON-RPC envelope

Requests use JSON-RPC 2.0. `jsonrpc` is exactly `2.0`; non-notification response `id` exactly echoes the request id. A notification is a request with no `id`; it has no response, including errors. The schema encodes this by allowing absent `id` on requests and by defining only non-null-id success envelopes. Success is `{ "jsonrpc": "2.0", "id": <id>, "result": <method-specific result> }`. Failure is `{ "jsonrpc": "2.0", "id": <id|null>, "error": { "code": <stable string>, "message": <string>, "data": <object> } }`. Wire shapes are normative in `docs/schema/api-v1.schema.json`.

The only v1 methods are `capabilities.get`, `snapshot.list`, `snapshot.get`, `topology.query`, `topology.reconcile`, `evidence.get`, `event.list`, and `health.get`. They are query-only. Job, live acquisition, subscription, mutation, and CNC write methods are absent and must return `METHOD_NOT_FOUND`. `capabilities.get` reports this surface explicitly.

Stable error codes are `INVALID_REQUEST`, `METHOD_NOT_FOUND`, `NOT_FOUND`, `INVALID_SOURCE`, `NOT_COMPARABLE`, `REMOTE_BIND_REJECTED`, `RESYNC_REQUIRED`, `UNRESOLVED_TOPOLOGY`, `STORAGE_UNAVAILABLE`, `MESSAGE_TOO_LARGE`, and `INTERNAL_ERROR`. `NOT_COMPARABLE` is returned by `topology.reconcile` when the requested Actual/Target pair cannot be compared under the published identity, representation, completeness, or selector rules; it is not a transport failure and is not interchangeable with `INVALID_REQUEST`. Its `error.data` is an object containing `reason` (`selector_mismatch`, `representation_mismatch`, `incomplete_snapshot`, `identity_mismatch`, or `unsupported_comparison`) and may contain the opaque `actual_snapshot_id` and `target_snapshot_id`. Identical Actual/Target IDs use `identity_mismatch`; representation or role incompatibility uses `representation_mismatch`. Error data is structured and contains no secrets.

## Method contracts

- `capabilities.get`: params `{}`; returns protocol/schema versions, method names, and `live_acquisition: false`.
- `snapshot.list`: params `{limit, cursor?, filters?}`; returns ordered summaries, `has_more`, `next_cursor`, and consistency metadata.
- `snapshot.get`: params `{snapshot_id}`; returns one immutable topology-v1 snapshot.
- `topology.query`: params `{snapshot_id, limit?, cursor?, filters?}`; returns selected topology records and pagination metadata.
- `topology.reconcile`: params `{actual_snapshot_id, target_snapshot_id}`; returns the separate reconciliation result.
- `evidence.get`: params `{evidence_id}`; returns one conforming evidence record.
- `event.list`: params `{limit, cursor?, filters?, from_event_id?, from_offset?}`; returns ordered events and replay metadata. Supplying both `from_event_id` and `from_offset` is invalid.
- `health.get`: params `{}`; returns storage/readiness health without starting work.

Limits are bounded by deployment policy. Cursors and replay tokens are opaque; clients must not decode or construct them. They bind method, canonical filters, consistency token, installation scope, schema version, and retention generation. Events are ordered by durable offset and deduplicated by immutable `event_id`. A supplied event ID or offset is exclusive.

When the start point or cursor is expired, unknown, filter-incompatible, or a queue gap occurred, return `RESYNC_REQUIRED` with all of `{earliest_retained_offset, requested_from_event_id, requested_from_offset, authoritative_snapshot_ids, reason}`; `authoritative_snapshot_ids` is non-empty. The client must obtain an authoritative snapshot and then use a fresh cursor. Snapshots are authoritative; events are hints.

The schema binds every request and response to its method. `snapshot.get {}` and `capabilities.get {snapshot_id}` are invalid. List methods have page metadata; `event.list` additionally has required replay metadata. Result objects are closed envelopes; arbitrary method-free `result` objects are not conforming. Schema-derived structural regression cases are documented in `schema/schema-derived-regressions.md`; they do not claim executable JSON Schema validation.

## Deployment and deferred transport

The core does not bind sockets. A deployment adapter checks the configured address before listen and permits loopback only by default (`127.0.0.0/8`, `::1`). Non-loopback is rejected before listen and audited as `REMOTE_BIND_REJECTED`; an ordinary request cannot override this. HTTP, WebSocket, framing, authentication, subscriptions, live acquisition, and reconnect transport are deferred.

## References

- `API_STAGE3_DESIGN.md` defines B1-B8, store ports, identity, artifact security, publication atomicity, retention/restart, and acceptance tests.
- `schema/api-v1.schema.json` defines machine-readable request/response/error/event shapes.
- `schema/evidence-v1-conformance.md` defines the evidence validator boundary and confirmed-relation gate.
