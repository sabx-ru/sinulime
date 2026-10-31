# Stage 16.5: Deep MCVar Async/Cyclic Static Research

## Scope

Offline reverse engineering only. Source archives and both MCVar binaries were read-only. No Windows executable, PCU package, client, collector, UI, DDE transport, or live hardware experiment was created or run.

## New verified knowledge

1. **ABI cross-version revalidation.** Eight target TypeInfos were normalized from the preserved old/new MSFT resources: `IVar`, `IVar2`, read/write callbacks v1/v2, `IMCCommand`, and `IMCCommandAsyncCallback`. The comparison contains 33 methods and reports `changed_count=0`. `IVar` and `IVar2` are distinct interface revisions, not the old/new versions of one interface. Exact descriptors and flags are preserved under `abi/`.
3. **Async request-ID boundary.** Follow-up byte analysis resolves that `ReadVarAsync` passes the caller's `pReqID` to the transaction starter; old `0x1000d842` / new `0x1000d954` stores it at transaction record offset `+0x98`. A downstream completion/result routine writes the generated value through that pointer at old `0x1000ff3e` / new `0x10010050`. Completion code also directly calls an interface vtable slot `+0x14` at old `0x1000fef1` / new `0x10010003`; nearby code prepares `OnDataChanged` diagnostics. This is direct callsite evidence, but the exact per-ReadVarAsync transaction linkage, callback method packing and timing remain unresolved.
4. **Async implementation entry (static).** The entry path allocates/initializes a 12-byte transaction/result record, performs callback/interface capability checks, and contains shared transaction-formatting branches with `StartRead`, `StartWrite`, and `StartExec` diagnostics. The `StartRead` branch and input preparation are direct evidence; the method is not characterized as exclusively following a read-only internal branch without a resolved predicate. The old/new legacy symbol at `0x1000d3f6`/`0x1000d508` overlaps the main body and is not accepted as an independently verified forwarding thunk.
5. **Cyclic subsystem.** Both binaries contain named `CCyclic`, `CCyclicID/ReqID`, `StartCyclic`, `DataChange`, `IdleCB`, `FlushCyclics`, removal, `CalculateRequestRates`, and `normalizeUpdateRate` paths. Rate input/output array handling and stored rate/deadband/critical fields are evidenced. New-build follow-up proves a conditional `FlushCyclics` call `0x100134ab -> 0x100139c2` under state bit `0x80000` at `[this+0x28]`; the helper is a callback-dispatch candidate. `DataChange -> pending`, `IdleCB -> FlushCyclics`, the helper's final indirect callback target and complete old-build causal chain remain unresolved.
6. **Ownership/threading.** Both builds import ATL QI/smart-pointer helpers, interlocked refcount operations, critical-section functions, timer/message APIs, and have Dispatch/Dual callback diagnostics. Direct evidence does not establish callback `AddRef`, request ownership, timer ownership, worker thread, apartment identity, or marshaling. No `CreateThread` import was identified in the reviewed imports; this does not prove absence of worker execution elsewhere.
7. **Collector implication.** Preserved PCU logs still make synchronous batched `ReadVar` the only `HISTORICAL_RUNTIME_PROVEN` mode. Async and cyclic remain capability-gated. The architecture matrix defines observation fields and runtime gates without claiming native callback support.

## Classification summary

- `STATIC_PROVEN`: TypeLib-decoded declarations and cross-version equality; exact async entry and bytes; direct call/record allocation/request preparation/result-validation instructions; existence of callback/cyclic helper code and diagnostic paths.
- `HISTORICAL_RUNTIME_PROVEN`: synchronous `ReadVar` behavior only, as recorded in earlier real-PCU evidence.
- `STATIC_INFERRED`: completion helper connects to async callback dispatch; cyclic linked-list/state interpretation; conceptual stateful scheduling path.
- `HYPOTHESIS`: `ReadVarAsync` is nonblocking; cyclic delivery is server-managed periodic push; callbacks require an STA message pump; `CriticalValues` is a threshold trigger.
- `UNKNOWN`: callback delivery/thread/ordering, precise callback slot and marshaling, request overlap limit, rate units/quantization, deadband semantics, critical-value semantics, removal matching and final cleanup.

## Review boundary

This report consolidates workstream artifacts and orchestrator cross-checks. Independent acceptance review returned CONDITIONAL PASS; its required overlap/thunk wording correction is applied below. Windows `ITypeInfo` and PCU runtime behavior remain outside available evidence.

## Review and Stage 16.6 checkpoint

Independent review verdict: **CONDITIONAL PASS**. Reviewer reproduced both binary hashes and `ReadVarAsync` entry bytes, validated the ABI JSON and 8 unchanged interface records, and confirmed that runtime claims remain unproven. Required wording correction has been applied: legacy symbols at old `0x1000d3f6` / new `0x1000d508` are overlapping analysis boundaries, not independently verified forwarding thunks. The shared `StartRead`/`StartWrite`/`StartExec` branch caveat is retained. New async/cyclic callsite evidence is recorded in `async_flow/followup/` and `cyclic_flow/followup/`; no complete runtime lifecycle is claimed.

## Safety

No source binary was changed. No write-capable MCVar method was invoked. No PCU was contacted. DDE/NCDDE research remained frozen.
