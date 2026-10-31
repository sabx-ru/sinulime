# Stage 16.5 Collector Architecture Decision Matrix

## Scope and evidence rule

This is an offline research/design artifact. It does not implement a collector, COM client, callback object, polling scheduler, Windows tool, or transport adapter. DDE remains frozen.

Claims use exactly these evidence classes:

- **STATIC_PROVEN**: directly recovered from preserved PE/TypeLib artifacts or decoded ABI records.
- **HISTORICAL_RUNTIME_PROVEN**: observed in preserved execution logs on the historical PCU/runtime; scope is limited to that build, host, and test.
- **STATIC_INFERRED**: a constrained interpretation of static evidence, useful for design but not execution proof.
- **HYPOTHESIS**: a testable architecture or behavior proposal, not established by evidence.
- **UNKNOWN**: evidence is insufficient; do not encode as a production assumption.

Static TypeLib decoding is evidence of what the resource encodes. It is not proof that the method can be invoked, returns asynchronously, delivers callbacks, or behaves identically on a deployed PCU.

## Recovered evidence baseline

| Evidence item | Classification | Consequence |
|---|---|---|
| Old/new embedded resources decode as `MCVARLib`, version 1.0, with `IVar`, `IVar2`, async callback interfaces, and matching target TypeInfo records. | STATIC_PROVEN | A transport-neutral capability description can name these operations and retain their exact ABI metadata. |
| `IVar2.ReadVar` is an HRESULT-returning Automation method with optional Names/ServerHandles and output values/errors/qualities/server info/timestamps as decoded VARIANT pointers. | STATIC_PROVEN | Synchronous result normalization must support per-item arrays, optional outputs, raw HRESULT, and absent source metadata. |
| `IVar2.ReadVarAsync` has callback pointer `IReadVarAsyncCallback2*`, `IDispatch*`, output `pReqID`, and optional output errors. | STATIC_PROVEN | Async can be represented as a gated capability; callback and request lifecycle must not be assumed operational. |
| `IVar2.ReadVarCyclic` has callback pointer, deadbands, requested/revised update rates, in/out request ID, optional critical values/errors. | STATIC_PROVEN | Cyclic configuration and returned revised rates belong in a prospective capability contract, not in the default runtime path. |
| Callback2 `OnDataChanged` encodes Values, TimeStamps, ClientHandles, optional Qualities/ServerInfos/Errors; legacy callback has Values, Qualities, ClientHandles. | STATIC_PROVEN | Callback normalization must tolerate missing optional metadata and distinguish source timestamps from local receipt time. |
| Historical PCU50.3 Windows XP x86 runs executed 277 `ReadVar` rounds: 261 outer `HRESULT=0`, 16 `0x80020009`. Batches of 1 through 20 worked in the saved tests. | HISTORICAL_RUNTIME_PROVEN | Synchronous batched ReadVar is the only proven acquisition basis. It remains bounded and build-scoped. |
| Historical 20-item timing median was about 115 ms for four series; the fitted equation is session/PCU-specific. | HISTORICAL_RUNTIME_PROVEN | No universal polling period, throughput, timeout, or optimal batch size may be derived. |
| Per-slot quality included 2752 `Quality=192` and 74 `Quality=0`; outer success did not imply every item was good. | HISTORICAL_RUNTIME_PROVEN | Item-level quality/error state is mandatory; outer HRESULT alone is insufficient. |
| Historical outputs included `VT_ERROR` timestamps in 272 accepted/error-context cases and `VT_EMPTY` in five rejected calls; source timestamp semantics were not established. | HISTORICAL_RUNTIME_PROVEN | Local receipt time and source timestamp must be separate; absent source time means freshness is unknown. |
| `MCVar.Var2` is advertised as Apartment-threaded in the recovered registration/evidence. | STATIC_PROVEN | An STA/single COM-owning worker is a deployment gate/design constraint until exact Windows behavior is validated. It is not proof that message pumping is sufficient for callbacks. |
| `ReadVarAsync`, `ReadVarCyclic`, `OnDataChanged`, and cyclic lifecycle strings exist in both old/new images. | STATIC_PROVEN | Names and static surface are real; runtime delivery, persistence, cancellation, removal, and thread identity remain unproven. |
| No preserved run proves callback delivery, nonblocking return, connection-point `Advise`/`Unadvise`, cyclic persistence, callback thread, or async cleanup. | UNKNOWN | Async/cyclic cannot be the default or silently selected by a feature flag. |
| Static MCVar-to-NCDDE transport/object identity was not recovered; general DDE API presence and counters do not prove the ReadVar route. | UNKNOWN | The collector contract must not expose DDE packet counts, atomicity, or backend transaction claims. |

## Architecture options

| Option | Evidence status | What it means | Decision |
|---|---|---|---|
| **Polling-backed synchronous `ReadVar`** | HISTORICAL_RUNTIME_PROVEN for the historical build; STATIC_PROVEN ABI; deployment portability beyond that build is UNKNOWN | A bounded scheduler issues synchronous `ReadVar` batches, one acquisition session at a time, and normalizes each returned slot. | **SELECT as baseline.** Keep the vendor boundary opaque and require runtime gates for each deployed image/PCU. |
| **Native async `ReadVarAsync`** | STATIC_PROVEN interface shape; runtime behavior UNKNOWN | One request returns a request ID and should later produce callback data, but immediate-return semantics, callback mechanism, threading, ordering, cancellation, and cleanup are unverified. | **CAPABILITY-GATED only.** Do not use for baseline collection or infer nonblocking behavior from the method name. |
| **Native cyclic `ReadVarCyclic`** | STATIC_PROVEN interface shape; runtime behavior UNKNOWN | A request ID, deadbands, requested/revised rates, and callback surface encode a possible recurring subscription. | **CAPABILITY-GATED only.** Do not equate revised rates or cyclic names with actual periodic delivery. |
| **Application-level cyclic behavior implemented by repeated synchronous reads** | HYPOTHESIS built on HISTORICAL_RUNTIME_PROVEN synchronous reads | Provides a subscription-like API while preserving the proven synchronous transport path. | **Preferred compatibility model for baseline design.** Its interval, load, and staleness policy require deployment measurement; no universal rate is prescribed. |
| **Transport-specific/DDE-derived collector contract** | STATIC_INFERRED at most; the invocation-specific MCVar transport edge is UNKNOWN | Would expose presumed DDE messages, packet counts, atomic snapshots, or broker semantics. | **Reject.** Keep transport details behind the adapter and record only observed API/result facts. |
| **Concurrent or multi-threaded vendor calls** | HYPOTHESIS; not runtime-proven and conflicts with Apartment caution | Could increase throughput or overlap requests. | **Reject for baseline.** Use one COM-owning STA/session and one outstanding operation until PCU evidence proves otherwise. |

## Decision matrix by requirement

| Requirement | Polling-backed synchronous | Native async | Native cyclic | Evidence/classification | Gate to change decision |
|---|---|---|---|---|---|
| Can acquire values on preserved historical PCU? | Yes, via saved `ReadVar` runs. | No evidence. | No evidence. | Polling: HISTORICAL_RUNTIME_PROVEN. Others: UNKNOWN. | Matching Windows runtime test. |
| ABI call shape | `ReadVar` and outputs are decoded. | `ReadVarAsync`, callback, request ID decoded. | `ReadVarCyclic`, callback, rates, request ID decoded. | STATIC_PROVEN. | Independent Windows `ITypeInfo`/`FUNCDESC` oracle on exact deployed DLL. |
| Nonblocking invocation | Not required; synchronous completion observed. | Not proven. | Not proven. | Polling: HISTORICAL_RUNTIME_PROVEN for completion; async/cyclic: UNKNOWN. | Measure call return before callback and record HRESULT/timing. |
| Per-item result preservation | Required and historically observed, including mixed outcomes. | Required in callback normalization but not observed. | Required in callback normalization but not observed. | Polling: HISTORICAL_RUNTIME_PROVEN; others: STATIC_INFERRED. | Callback arrays and client-handle alignment test. |
| Item quality and errors | Required; outer `S_OK` is insufficient. | Callback optional quality/errors are ABI-encoded, delivery unknown. | Same. | Polling: HISTORICAL_RUNTIME_PROVEN; callback fields: STATIC_PROVEN. | Mixed valid/invalid and quality/error callback run. |
| Source timestamps | Optional output exists; historical source availability/meaning unproven. | Callback2 names timestamps; delivery/meaning unproven. | Same. | STATIC_PROVEN field; semantics UNKNOWN. | Verify values, VARIANT types, source clock, and missing-value behavior. |
| Subscription/change-only behavior | Application policy can compare successive synchronous results. | Callback delivery/change policy unknown. | Names/deadbands suggest it, but behavior unknown. | Application policy: HYPOTHESIS; native: UNKNOWN. | Observe unchanged values, quality-only changes, deadbands, and callback frequency. |
| Cancellation/removal | Stop scheduling; no vendor subscription to remove. | `Cancel` is statically present; semantics unknown. | `RemoveCyclicVariables` is statically present; semantics unknown. | Static methods: STATIC_PROVEN; behavior UNKNOWN. | Start, cancel/remove, then prove no later callbacks and no leaked request. |
| Ordering and concurrency | Serialize by policy; one outstanding operation. | Request/callback ordering and overlap unknown. | Multiple subscription ordering unknown. | Baseline policy: HYPOTHESIS supported by STA caution. | Concurrent bounded experiment with request IDs and callback sequence numbers. |
| Reconnect behavior | Application lifecycle policy; vendor recovery semantics unknown. | Request survival/replay unknown. | Subscription persistence across disconnect unknown. | UNKNOWN for vendor semantics. | Disconnect/reconnect test with explicit cleanup and re-registration. |
| Timing/rate selection | Historical 20-item median only; no universal rate. | No callback latency distribution. | No revised-rate semantics/runtime. | Historical timing: HISTORICAL_RUNTIME_PROVEN; rates: UNKNOWN. | Controlled p50/p95/p99 run on exact deployment target. |
| Thread/apartment requirement | Use one STA COM owner as conservative deployment constraint. | Callback thread/marshaling unknown. | Callback thread/marshaling unknown. | Registration: STATIC_PROVEN; operational requirement: STATIC_INFERRED. | Record apartment, callback thread, message-pump dependence, and reentrancy. |

## Transport-independent collector contract

The contract is deliberately expressed in observations and lifecycle, not DDE, packet, or presumed broker terms.

### Request

A request contains:

- ordered signal identifiers exactly as supplied by the catalogue;
- optional server handles only when obtained and validated for the same session;
- a bounded batch size selected by policy, with 20 as the historical tested ceiling, not a vendor maximum;
- cache policy as an explicit requested value, with no claim about cache implementation or freshness;
- monotonic deadline and correlation ID;
- acquisition mode label: `polling`, `async`, or `cyclic`.

### Per-item observation

Every returned position, including failures, retains:

- request correlation ID and input position;
- signal identifier and optional server/client handle;
- value, or explicit absence;
- raw vendor quality, if supplied;
- normalized quality only when mapping is justified;
- raw per-item error and outer HRESULT;
- `request_started_at` and `response_received_at` using a local monotonic/operational clock;
- source timestamp only when the vendor actually supplies a usable one;
- freshness state: `FRESH`/`STALE` only with a defensible source or explicitly defined local policy, otherwise `UNKNOWN`;
- mode and runtime/build provenance.

A failed read must not convert the prior value into a current/fresh value. Retaining a prior value is permitted only with explicit age and `UNAVAILABLE` (or another justified non-good state). The contract must preserve duplicate and positional inputs; it must not key solely by signal name.

### Lifecycle

The mode-neutral lifecycle is:

`created -> capability_checked -> connected -> acquiring -> delivered | failed -> reconnecting -> stopped`

For native async/cyclic, add request/subscription identifiers and explicit `cancel/remove` completion states. A method returning an HRESULT or request ID is not itself delivery proof. Shutdown must stop new work, cancel/remove only when that capability has passed its runtime gate, drain/mark outstanding work, release COM-owned objects on the owning apartment, and record cleanup outcome.

### Capability gates

A mode may be enabled on a deployment only after all applicable gates pass:

1. **Identity gate:** exact MCVar DLL/TypeLib hashes, bitness, registration, OS, and PCU/provider identity recorded.
2. **ABI gate:** Windows `LoadTypeLibEx(REGKIND_NONE)` and `ITypeInfo::GetFuncDesc` agree with the recovered decoded records, including IIDs, parameter flags, referenced types, calling convention, and vtable offsets.
3. **STA gate:** object creation, invocation, message-pump behavior, marshaling, reentrancy, and release are observed from the intended apartment model.
4. **Result gate:** bounded 1/5/20 cases, duplicates, lower bounds, mixed valid/invalid addresses, outer/per-item HRESULT behavior, quality, and optional outputs are recorded.
5. **Async gate:** immediate return, request ID, callback interface/`IDispatch` path, callback thread, ordering, errors, cancellation, and no-callback timeout are demonstrated.
6. **Cyclic gate:** requested versus revised rates, deadband/change semantics, grouping, callback behavior, suspend/resume, removal, disconnect/reconnect, and no post-removal callbacks are demonstrated.
7. **Operational gate:** timeout/reconnect/cleanup behavior, bounded resource usage, and a controlled latency/failure profile meet deployment requirements.

Until gates 1-4 pass, use only the polling baseline. Until gates 5 or 6 independently pass, async or cyclic are unavailable, regardless of static names or ABI completeness.

## Exact questions for PCU validation

Run only bounded, read-only experiments against the authorized exact PCU build; preserve raw logs, executable hashes, HRESULTs, request IDs, callback sequence, thread IDs, monotonic timestamps, and cleanup results.

1. What exact MCVar DLL/TypeLib file hashes, OS build, bitness, registration state, MCVar class/IID, and provider/NC configuration are present?
2. Does Windows `LoadTypeLibEx(REGKIND_NONE)` return the same library identity, IIDs, method order, `memid`, `oVft`, calling convention, parameter flags, optionality, and referenced TypeInfos recovered offline?
3. Does `IVar2.ReadVar` accept the historical 1, 5, and 20 item shapes on this PCU, including duplicates, non-zero SAFEARRAY lower bounds, mixed valid/invalid addresses, and `CacheDevice` values 0/1/2?
4. For each synchronous case, what are outer HRESULT, per-item error, quality, value, server-info, timestamp VARIANT type/value, request-start time, response time, and last-success time?
5. Does an outer `S_OK` coexist with per-item failures on this exact build, and what exact rule determines an outer exception versus an item error?
6. Is the returned batch an atomic snapshot, or can values change between positions? Record a controlled changing-signal experiment; do not infer atomicity from array shape.
7. Does `ReadVarAsync` return before data delivery? Record call duration, immediate HRESULT, output request ID, callback arrival, callback count, and whether a callback can arrive before the call returns.
8. Does async delivery use the decoded `IReadVarAsyncCallback`/`2` vtable, an `IDispatch` sink, both, or neither? Which IID is queried or invoked?
9. On which thread and COM apartment does `OnDataChanged` execute? Does delivery require a message pump, and what happens when the pump is paused?
10. Are callback Values, ClientHandles, optional Qualities, ServerInfos, Errors, and TimeStamps positionally aligned? What VARIANT types and bounds are delivered for each?
11. What is the async request-ID lifecycle: uniqueness, reuse, outstanding-request limit, completion ordering, timeout behavior, duplicate callbacks, and error callback behavior?
12. What does `Cancel(ReqID)` do before completion, after completion, and after callback delivery? Is cancellation synchronous, and can a callback race with cancellation?
13. Does `ReadVarCyclic` create a recurring subscription on this PCU? Record immediate HRESULT, in/out request ID, requested rates, revised rates, deadbands, and first/steady-state callback timing.
14. Are cyclic callbacks change-only, periodic regardless of change, quality-only, deadband-filtered, or grouped across signals? Test unchanged values, value changes below/above deadband, quality changes, and invalid addresses.
15. What are the units, minimum, maximum, and quantization rules for `RequestedUpdateRates` and `RevisedUpdateRates`? Are rates per item, per request, or provider constrained?
16. Does `RemoveCyclicVariables(ReqID)` remove the complete request, selected names, selected server handles, or some combination? Prove no callbacks after removal and record returned errors.
17. What do `Suspend(ReqID)` and `Resume(ReqID)` do to revised rate, queued data, callback ordering, and request identity?
18. What happens to async and cyclic requests across provider disconnect, COM reconnect, PCU service restart (if separately authorized), and client shutdown? Are subscriptions retained, dropped, or replayed?
19. Can two clients or two requests overlap safely? Test only bounded concurrency after the single-flight baseline and record cross-request callback/order isolation.
20. Which timestamps are source timestamps, which are local receipt timestamps, and what exact sentinel/VARIANT is returned when source time is unavailable?
21. Are callback pointers validated, and what is the behavior for null, wrong-interface, released, or deliberately nonresponsive callback objects? Keep the experiment non-destructive and bounded.
22. Does cleanup release all request/subscription objects on the STA without late callbacks, leaks, or access violations? Record shutdown order and final HRESULTs.

## Current decision

Adopt a **polling-backed synchronous baseline** behind a narrow, transport-independent acquisition contract. Treat native async and cyclic as optional capabilities whose static ABI is recovered but whose runtime gates are open. Do not claim DDE routing, backend transaction count, atomic snapshots, source freshness, callback delivery, or universal timing until the corresponding PCU evidence exists.
