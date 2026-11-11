# Stage 1 contract acceptance matrix

**Status:** normative Stage 1 design gate; Stage 2 envelope validation, legacy replay, and B3 additive B2 identity projection are implemented.

The topology-v1 schema was intentionally adopted by the Stage 2 envelope projection. Its manifest entry records the exact current size and SHA-256; legacy `evidence.json` and captured inputs remain unchanged.

| Area | Contract acceptance | Stage 1 status | Blocking condition |
|---|---|---|---|
| Layer boundaries | Acquisition, decoding, topology resolution, evidence, state, persistence, and API remain separated and transport independent. | Accepted | None |
| Actual/Target | Both sides use graph or `{ "availability": "unavailable", "reason": "..." }`; `null` is invalid for unavailable data. | Accepted | Schema/prose/examples must stay aligned. |
| Endpoint selectors | Schema has explicit branches for physical_device, logical_object, channel, port, and object selectors. | Accepted | Branch changes require schema and example updates. |
| Evidence gate | Confirmed connections and representation/CU_LINK relations require rule_id, immutable rule_version, checks with minItems 1, and evidence_ids with minItems 1. | Accepted | No confirmed relation may bypass the gate. |
| Sparse sensor index | Original source index must survive filtering and parallel lookup; missing/duplicate/ambiguous index yields unresolved/ambiguous_mapping. | **Blocked** | Stage 2 developer implementation fix plus contract test required. |
| API event replay | `event.list` defines from_event_id/from_offset, exclusive precedence, replay metadata, earliest retained offset, and RESYNC_REQUIRED data. | Accepted | Implementation is later Stage 2/API work. |
| Baseline reproducibility | Canonical relative path, byte size, and SHA-256 are recorded for the agreed input set. | Accepted | Manifest excludes itself and volatile caches. |
| B3 envelope identity | Additive topology100 projection uses canonical B2 IDs; unsupported object-kind identity contracts stay provisional and snapshot scoped. | Implemented with documented identity gaps | No legacy ID mapping; no confirmed relations through provisional endpoints. |

## Readiness verdict

Stage 1 architecture and schemas are contract-complete. B3 identity projection is additive and verified offline; broader implementation readiness remains gated. B3 does not define canonical source identities for legacy axis/component/drive record kinds, which remain provisional until those domain contracts specify exact selectors and ambiguity rules.

## Required Stage 2 contract test

Given a sensor source with sparse original indices, filter and decode it through the production path. Assert that each retained observation and every dependent relation carries the original source index, never its post-filter enumeration position. Include missing, duplicate, and ambiguous index cases and assert `unresolved` plus `ambiguous_mapping`; assert that no such relation is `confirmed`.
