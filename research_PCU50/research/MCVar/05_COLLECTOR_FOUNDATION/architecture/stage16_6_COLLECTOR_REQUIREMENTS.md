# Stage 16.6 Collector Requirements

## Purpose and boundary

Translate the corrected Stage 16.5 static findings into requirements for a future collector. This is an architecture artifact only: it implements no collector, COM client, callback sink, Windows tooling, scheduler, or transport. It makes no claim that MCVar async/cyclic behavior is native, asynchronous, recurring, or operational. DDE/NCDDE is out of scope.

Use evidence labels consistently:

- **STATIC_PROVEN**: directly encoded in the recovered TypeLib or established by preserved binary bytes/instructions.
- **HISTORICAL_RUNTIME_PROVEN**: observed in preserved PCU execution logs; scoped to the tested build, host, and case.
- **STATIC_INFERRED**: a constrained interpretation useful for design, not proof of runtime behavior.
- **SAFEGUARD**: a conservative design rule adopted because the evidence does not establish a safer alternative.
- **RUNTIME GATE**: evidence that must be collected on the intended deployment before enabling a capability.
- **UNKNOWN**: unresolved; must not be silently promoted to a production assumption.

## Proven evidence and collector consequences

| Evidence | Class | Requirement consequence |
|---|---|---|
| Old/new TypeLib resources decode the target `IVar`, `IVar2`, and callback TypeInfos. The normalized target records compare equal across both resources. The corrected direct-function count is 32 across eight target TypeInfos. | STATIC_PROVEN | Preserve exact interface identity and ABI metadata per DLL; do not describe the direct-function count as 33. Independently validate metadata on Windows for each deployed image. |
| `ReadVarAsync` and `ReadVarCyclic` declarations encode callback, request-ID, and optional/result parameters. Callback2 `OnDataChanged` declares values, timestamps, client handles, and optional qualities/server info/errors; legacy callback declares values, qualities, and client handles. | STATIC_PROVEN | A future adapter may model these declared shapes, but must accept missing optional fields and preserve input/output distinctions from verified ABI records. Declarations do not establish invocation or semantics. |
| In both builds the call at old `0x1000fef1` / new `0x10010003` uses vtable slot `+0x14` with arguments matching `IDispatch::GetIDsOfNames`; the name pointer is UTF-16 `OnDataChanged`. | STATIC_PROVEN | Treat this as name resolution only; do not count it as delivery. |
| A separate callback routine has a `+0x18` `IDispatch::Invoke`-shaped call at old `0x100146a0` / new `0x100147aa`; the DISPID-like local from the lookup is passed to it, with nearby `Dispatch "OnDataChanged" called` and HRESULT diagnostics. | STATIC_PROVEN_CALLSITE; dataflow STATIC_INFERRED | Static dispatch attempt is established in that routine; runtime success and reachability from each request remain unknown. |
| Static evidence separately contains a vtable `+0x14` indirect call discussed as a possible callback-interface path, as well as a transaction-object `+0x04` call. The final method/interface binding to a particular `ReadVarAsync` request and timing are unresolved. | STATIC_PROVEN callsites; UNKNOWN linkage | Do not identify either call as proven ReadVarAsync completion delivery absent further evidence. |
| Async starter stores caller `pReqID` at transaction record offset `+0x98`; a downstream completion/result routine writes a generated value through a stored output pointer. | STATIC_PROVEN | Treat request-ID publication as potentially later than method entry; record call return and output-ID observation separately. Do not infer completion from an ID being returned or populated. |
| Both binaries expose cyclic creation/removal and named `DataChange`, `IdleCB`, `FlushCyclics` machinery. New-build `FlushCyclics` traverses list-like structures and conditionally calls helper `0x100139c2`; helper callback identity and upstream causal edges are unresolved. | STATIC_PROVEN local operations; UNKNOWN full chain | Model cyclic as an unverified capability. Do not claim a complete data-change-to-callback chain, server-managed periodic delivery, or a proven scheduler. |
| Callback AddRef/Release ownership, request cleanup, callback thread/apartment, marshaling, and complete cancellation/removal lifecycle are unresolved. Module imports and diagnostics do not settle these questions. | UNKNOWN | Require explicit lifetime/thread tests; do not assume callback retention, automatic marshaling, thread affinity, or safe shutdown. |
| Preserved historical PCU logs prove synchronous batched `ReadVar` only, for the tested PCU50.3 Windows XP x86 context and batches 1..20. Item quality/errors can differ despite outer success. | HISTORICAL_RUNTIME_PROVEN | Keep synchronous bounded reads as the only evidence-backed baseline. Preserve each item result and outer HRESULT independently. Historical timing and batch ceiling are not universal limits. |

## Future collector requirements

### Baseline acquisition

1. Use synchronous `ReadVar` as the baseline acquisition path. Any other mode is disabled unless its own runtime gate passes on the exact deployment.
2. Serialize vendor calls through one COM-owning STA/session as a **SAFEGUARD**. Do not overlap calls or infer that a message pump makes callbacks safe. Revisit only with measured apartment, reentrancy, and concurrency evidence.
3. Keep the vendor adapter narrow and transport-neutral. Record observed API calls and results only; expose no presumed DDE packets, backend transaction counts, atomic snapshots, or server freshness.
4. Bound request sizes and deadlines by explicit application policy. Historical 1..20 batches are test evidence, not an MCVar maximum or universal performance target.
5. Preserve ordered positional results, duplicates, and per-item failures. Never reduce outcome to outer HRESULT alone or key results only by signal name.

### Observation and provenance

For every request and returned position, a future collector must preserve:

- exact input position and signal identity; session-valid server/client handles only when actually obtained;
- value or explicit absence, raw quality, per-item error, and outer HRESULT;
- local request-start and response-received times, kept distinct from any source timestamp;
- source timestamp only when actually supplied and validated; missing/invalid source time means freshness `UNKNOWN` absent a separately defined local policy;
- acquisition mode, exact DLL/TypeLib identity, PCU/provider and OS/bitness provenance, and capability-gate result;
- request correlation ID; for async/cyclic, vendor request/subscription ID, callback sequence and receipt time when observed.

A failed read must not make a retained previous value appear current. If last-known values are retained, report their age and unavailable/error state explicitly.

### Async capability, if later enabled

- Treat `ReadVarAsync` as a statically declared capability only. Do not infer nonblocking return, eventual callback, delivery order, or completion from its name, ABI, request ID, callback name lookup, or static implementation clues.
- Keep the `IDispatch` path stages distinct: `GetIDsOfNames` at old `0x1000fef1`/new `0x10010003`, the separate `Invoke`-shaped call at old `0x100146a0`/new `0x100147aa`, and actual user callback execution. Static evidence establishes the first two stages and a DISPID-like local flow, but does not establish per-request reachability or runtime success.
- Test typed callback-interface invocation separately from IDispatch delivery and establish which interface is actually used. Preserve callback fields positionally, including optional metadata and array bounds/types.
- Define an explicit request state machine with separate invocation result, request-ID publication, callback/result, error, timeout/no-callback, cancellation, and cleanup outcomes. A returned HRESULT or request ID is not completion.
- Do not assume a callback pointer is retained, AddRef'd, checked, marshaled, or safe to release. Shutdown and cancellation behavior remain gated on observed lifetime semantics.

### Cyclic capability, if later enabled

- Treat `ReadVarCyclic` as a static API shape, not proof of a recurring subscription or change-only delivery.
- Keep requested and revised rates as raw values until units, normalization, bounds, and meaning are measured. Do not label revised rates as negotiated periods without evidence.
- Preserve deadband and critical-value inputs as configuration; do not assign trigger semantics from parameter names.
- Require observed creation, first delivery, steady-state behavior, suspend/resume, per-variable removal, request cancellation, disconnect/reconnect, and final cleanup before operational enablement.
- Establish that removal/cancel prevents later callbacks, including races already in flight. Do not assume request-ID scope, matching precedence, or empty-array behavior.
- Do not claim `DataChange -> pending -> IdleCB -> FlushCyclics -> callback` as established. The verified new-build flush-to-helper call is conditional and does not establish helper identity or the upstream path.

## Runtime gates

No async/cyclic capability is enabled in a deployment until its applicable gates pass and raw evidence is retained.

1. **Identity and ABI:** record exact DLL and TypeLib hashes, OS/PCU/provider, bitness, registration and interface IDs. On Windows, compare `LoadTypeLibEx(REGKIND_NONE)`/`ITypeInfo` descriptors with recovered records, including parameter flags, referenced types, method order and vtable offsets.
2. **STA and invocation:** establish object creation, owning apartment, message-pump dependence, reentrancy, callback thread/apartment, and release behavior. Do not infer marshaling from COM interfaces or module imports.
3. **Synchronous result baseline:** exercise bounded 1/5/20 batches, duplicates, SAFEARRAY bounds, mixed valid/invalid items, outer/per-item HRESULTs, qualities, and optional outputs. Record actual duration distributions on target hardware.
4. **Async delivery:** measure call return versus callback timing; verify output request-ID timing; demonstrate actual typed callback or IDispatch invocation (including resolved DISPID and `Invoke` where applicable); record callback count/order/thread/arguments and no-callback timeout behavior.
5. **Async lifecycle:** test cancellation before and after completion, callback/cancel races, errors, shutdown, late callbacks, object release, and absence of leaks/use-after-release. Establish callback ownership rather than assuming it.
6. **Cyclic behavior:** measure requested/revised rates and observed cadence; test unchanged values, changes around deadband, quality-only changes, invalid inputs, suspend/resume, partial/full removal, cancellation, and no post-removal callback.
7. **Operational resilience:** exercise disconnect/reconnect and controlled shutdown; establish cleanup outcomes, bounded resource use, timeout behavior, and target-specific latency/failure acceptance criteria.

Until gates 1-3 pass, use only the gated synchronous baseline. Async and cyclic remain unavailable until their own gates pass independently; passing one does not enable the other.

## Open questions retained

- Which async/cyclic requests reach the static `Invoke`-shaped callback routine, and when? Is a separate dual/vtable callback path actually used for `ReadVarAsync`?
- Which concrete completion call is associated with a `ReadVarAsync` transaction, and can completion occur before the initiating method returns?
- What retains the callback object and request state; how are `AddRef`/`Release`, cancellation, owner release, and cleanup ordered?
- What thread/apartment executes callbacks, and is cross-apartment marshaling performed by another component?
- What is the complete cyclic causal chain from data arrival to callback? What are rate, deadband, critical-value, removal, suspend/resume, and reconnect semantics?
- Are old/new static similarities sufficient for a given deployed image? Runtime equivalence remains unproven.

## Evidence sources

- Stage 16.5 architecture baseline: `/root/PL/stages/stage16_5/architecture/COLLECTOR_ARCHITECTURE_DECISION_MATRIX.md`.
- Stage 16.5 research and static boundaries: `/root/PL/stages/stage16_5/reports/STAGE_REPORT.md`, `/root/PL/stages/stage16_5/async_flow/followup/readvar_async_boundary.md`, `/root/PL/stages/stage16_5/cyclic_flow/followup/STAGE16_6_CYCLIC_CAUSAL_EDGES.md`, `/root/PL/stages/stage16_5/ownership/ownership_callback_threading_report.md`, `/root/PL/stages/stage16_5/abi/README.md`.
- Corrected static evidence, superseding prior `+0x14` callback-delivery interpretation: `/root/PL/stages/stage16_6/corrections/STAGE16_5_CORRECTIONS.md` and the `corrections/dispatch/` instruction captures.
