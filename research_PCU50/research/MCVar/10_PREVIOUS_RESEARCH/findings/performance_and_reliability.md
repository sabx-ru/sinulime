# Performance and Reliability

## Available measurements

The saved Windows test logs contain whole-ReadVar `elapsed_ms` samples for sizes 1, 2, 5, 10 and 20. Size 40 is absent; per-item timing, CPU, memory, controlled throughput, timeout rate under load and P95/P99 across adequate samples are unavailable. Sample mix is not randomized/balanced, so no optimal polling rate or batch size is claimed.

## Cache, quality and timestamps

CacheDevice 0/1/2 were accepted in saved cases, but causality, cache layer, invalidation, TTL and freshness semantics are unknown. Successful quality values (usually `0x00C0`) are observations without proven source semantics. `pTimeStamps` and `pServerInfos` were observed unavailable in tested outputs. Do not fabricate source timestamps or server identity.

SDK states are application-level:

- `GOOD/UNCERTAIN/BAD/UNAVAILABLE` only where the adapter provides justified mapping; raw vendor quality should be retained.
- `FRESH/STALE/UNKNOWN` uses a source timestamp only if one is actually supplied; otherwise freshness is unknown or based on last local observation with explicit labeling.
- Request-start, response-received and last-success times must be distinct fields.

## Lifecycle and reliability policy

`MCVar.Var2` registration advertises Apartment threading. Use a single COM-owning worker/STA until Windows testing confirms marshaling, message pumping, reentrancy and concurrent-call safety. The portable SDK serializes adapter calls, but this is an orchestration model, not proof of vendor requirements.

Use bounded batches, one outstanding operation per session, finite retries only for classified transient transport failures, monotonic deadlines, capped reconnect backoff and no catch-up queue. On failed reads retain the last good value only with `UNAVAILABLE` quality and explicit age; never label it current. No controller/service restart is automatic.

## Runtime readiness

No live Windows COM/PCU test was run. Before deployment, validate apartment lifecycle, first read, 1/5/20 batches, per-item outputs, timeout behavior, clean disconnect/reconnect and cleanup on the exact deployed MCVar build. Extended rates, concurrent clients and cyclic reads require separate bounded authorization.
