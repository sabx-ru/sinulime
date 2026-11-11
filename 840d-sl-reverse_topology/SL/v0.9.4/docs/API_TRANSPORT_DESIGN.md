# API Transport Design

**Status:** DECIDED — transport remains deferred; API v1 stays transport-neutral.

## Decision

Do not add a WebSocket dependency to `requirements.txt` or `.venv-test` for v0.9.4. Do not implement WebSocket, HTTP, framing, authentication, subscriptions, reconnect, or socket binding in the production core.

The current project policy supports Python **3.12 and 3.13 x64**. The available test environment is Python **3.13.5**. The normative API contract is explicitly transport-neutral and the current dependency set contains only `python-snap7==2.0.2` and `pytest>=8.0`. Therefore adding `websockets` now would make an unexercised adapter dependency part of the installation contract without a transport implementation or transport acceptance tests.

A future transport work item may propose `websockets` (with a version range pinned by that work item's compatibility test), but it must be an adapter dependency, not a production-core dependency. That work item must define protocol framing, maximum message size, close/error mapping, loopback bind enforcement, authentication/authorization, origin policy, bounded queues, reconnect semantics, and tests against the supported Python versions before changing requirements.

## API error alignment

`NOT_COMPARABLE` is a normative v1 error code. It is emitted by `topology.reconcile` when the requested Actual/Target pair cannot be compared under the domain comparison rules. It represents a valid request whose comparison result is unavailable or undefined; it is not a malformed request, transport error, storage error, or generic conflict. It must not be remapped to `INVALID_REQUEST` or an HTTP/WebSocket-specific status in the core.

The error envelope remains:

```json
{
  "jsonrpc": "2.0",
  "id": "request-id",
  "error": {
    "code": "NOT_COMPARABLE",
    "message": "comparison is not defined for these snapshots",
    "data": {
      "reason": "identity_mismatch",
      "actual_snapshot_id": "actual-id",
      "target_snapshot_id": "target-id"
    }
  }
}
```

The `reason` value is one of `selector_mismatch`, `representation_mismatch`, `incomplete_snapshot`, `identity_mismatch`, or `unsupported_comparison`. Snapshot identifiers in `data` are optional opaque identifiers; no filesystem paths, credentials, or raw secrets are allowed. The canonical code list is aligned across `application/dto.py`, `docs/API_CONTRACT_V1.md`, and `docs/schema/api-v1.schema.json`.

## Developer scope after this gate

The next implementation task is limited to contract alignment and tests:

- preserve `NOT_COMPARABLE` in the application error mapping;
- add schema/contract fixtures for each permitted `NOT_COMPARABLE.reason` and reject unknown reasons at the application/domain validator boundary;
- verify that `topology.reconcile` returns `NOT_COMPARABLE` for identity, representation, completeness, and selector mismatches while preserving Actual and Target identifiers;
- verify that transport remains absent from the core and that no requirements change is made by this gate.

WebSocket adapter implementation, dependency selection, and transport tests are a separate explicitly scoped task.
