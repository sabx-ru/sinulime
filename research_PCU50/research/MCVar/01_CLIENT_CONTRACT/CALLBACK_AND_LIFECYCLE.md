# Callback and Client Lifecycle Contract

## Evidence boundary

Offline static analysis only; no Windows execution or runtime behavior is claimed. The matched old/new 32-bit `MCVar.dll` hashes are `43a5c1991d98b6b6e155233a0114d7ff72bf4dec7edf58d0607da501e7d98712` and `5e7d955ebe7cfd52424b04e91471b7408f42bf6cc427e3d94c50bc7f4428c24a`. Public method declarations and vtable target addresses are recorded in the canonical root `MCVAR_COM_ABI.json`; source disassembly and dataflow qualification are in `stages/stage16_7` evidence, with anchors below. Recommendations are conservative client policy, not claims about server guarantees.

## Request identity and state model

Treat an async request and a cyclic subscription as distinct client-side entities. Keep each caller's `pReqID` output storage alive and writable for as long as the operation may complete: `ReadVarAsync` passes that pointer through to the starter, which stores it at transaction-record `+0x98` (old `0x1000d819`, `0x1000d842`; new `0x1000d92b`, `0x1000d954`). This is pointer storage, not evidence that `+0x98` contains a numeric ID. The starter returns a transaction-record pointer in `EAX`; the wrapper separately stores that pointer at `+0x04`. A scalar read from `+0x20` is passed to a RID formatter, but its origin and identity with the eventual output value are unresolved. Never treat a transaction pointer, output pointer, scalar request ID, or cyclic ID object as interchangeable.

Recommended client states are `Submitting` (call in progress; output not yet trusted), `Pending` (call accepted and an ID actually observed in documented output), `Terminal` (completion/error callback observed), and `Retired` (client no longer uses ID). Do not infer acceptance, cancellation, or exactly-once completion from static code. If ID output is absent, unchanged, or ambiguous, do not manufacture an ID or use a default numeric value for removal. Preserve opaque ID bits exactly as supplied; do not assume generation scheme, sign, ordering, uniqueness scope, reuse behavior, or validity across object instances/processes. Serialize identity with the owning COM object and operation kind in the client registry.

Coexistence policy: maintain independent records for each async operation and each cyclic subscription, even if returned numeric values match. Do not deduplicate or cross-remove based on a shared numeric value. Static evidence explicitly separates `CTransactionID` lifecycle from `CCyclicID` and its list; no common identity namespace is established.

## Callback registration and delivery contract

### Public registration surface

The TypeLib defines two callback-related inputs on `ReadVarAsync` and `ReadVarCyclic`:

- `pCB`: typed `IReadVarAsyncCallback*` or `IReadVarAsyncCallback2*` interface pointer, depending on `IVar` versus `IVar2`.
- `pDisp`: `VT_DISPATCH` dispatch pointer.

The decoded callback interfaces are dual, Automation, dispatchable, `CC_STDCALL` interfaces. Their `OnDataChanged` contracts are:

```text
IReadVarAsyncCallback::OnDataChanged(
    VARIANT Values, VARIANT Qualities, VARIANT ClientHandles) -> HRESULT

IReadVarAsyncCallback2::OnDataChanged(
    VARIANT Values, VARIANT TimeStamps, VARIANT ClientHandles,
    [optional] VARIANT Qualities,
    [optional] VARIANT ServerInfos,
    [optional] VARIANT Errors) -> HRESULT
```

The TypeLib proves parameter names/order, VARIANT types, directions, and optionality. It does not prove SAFEARRAY element types, array shape, item ordering, missing-value representation, callback thread, or callback timing. Validate each received VARIANT before use.

Client registration policy:

1. Create the callback object and, when used, the dispatch object before submitting the operation.
2. Keep strong client/COM references to every object used for `pCB` or `pDisp` until the operation is explicitly terminal, removed, or otherwise quiesced by a separately documented contract.
3. Keep `pReqID` output storage writable for the entire period in which the implementation may write it. It is not the transaction pointer and is not proven to be the numeric ID itself.
4. Treat callback handling as re-entrant and cross-thread until runtime evidence establishes otherwise. Make handlers idempotent and avoid blocking calls into the same COM object.
5. For cyclic subscriptions, call `RemoveCyclicVariables` and retain callback resources through the client's own quiescence rule. The raw evidence does not prove that removal is a drain barrier.

These are safe client obligations. They must not be restated as claims that the vendor implementation uses a particular AddRef/Release order.

### Proven request retention and unresolved field identity

Both exact old/new `ReadVarAsync` slices directly call a shared starter and store three pointer-like inputs in the transaction record:

| Build | Entry -> starter | Stores for callback/dispatch-related inputs |
|---|---|---|
| old | shared internal slice `0x1000d28a`, call `0x1000d2d5` -> `0x1000d7a4` | `+0x84`, `+0x88`, `+0x90` at `0x1000d826`, `0x1000d82c`, `0x1000d832` |
| new | shared internal slice `0x1000d39c`, call `0x1000d3e7` -> `0x1000d8b6` | `+0x84`, `+0x88`, `+0x90` at `0x1000d938`, `0x1000d93e`, `0x1000d944` |

This proves request-side retention of pointer-like callback/dispatch-related values. It does **not** identify which offset is `pCB`, which is `pDisp`, or whether all three fields are used for delivery. Do not expose these offsets as a client ABI and do not hard-code a `pCB`/`pDisp` mapping.

### Observed late-bound route

The strongest common old/new dispatch shape is:

```text
ReadVarAsync -> starter -> retained callback/dispatch-related values
  -> helper region -> IDispatch::GetIDsOfNames("OnDataChanged")
  -> DISPID-like local -> IDispatch::Invoke-shaped call
```

The name-resolution sites are old `0x1000fef1` / new `0x10010003`, using UTF-16 `OnDataChanged` at old `0x100320cc` / new `0x1003311c`, with vtable slot `+0x14` (`IDispatch::GetIDsOfNames`) and an immediate HRESULT check. Separate `MakeCB` slices contain two different call shapes: the dispatch helper endpoints old `0x100146a0` / new `0x100147aa` end in `call [ecx+0x18]` (`IDispatch::Invoke`), while old `0x10013ad2` / new `0x10013bdc` end in `call [ecx+0x1c]`. With the dual callback interface layout (IUnknown slots 0-2, IDispatch slots 3-6), `+0x1c` is the first interface-specific vtable slot and is consistent with typed `OnDataChanged`, not `IDispatch::Invoke`. At those latter sites `ecx` is loaded from the vtable of the object at `[ebx+0x10]`; static bytes do not establish that object's identity as `pCB`, `pDisp`, or a particular request's callback.

The observed Invoke-shaped argument values are:

```text
this        = [ebx+0x14]
DISPID      = local [var_14h]
riid        = IID_NULL-like local storage
lcid        = 0x800
wFlags      = 1
pDispParams = &var_28h
pVarResult  = 0
pExcepInfo  = 0
puArgErr    = 0
```

Six 16-byte-looking copy blocks prepare a local value area before `pDispParams` is passed. `cArgs`, `cNamedArgs`, the exact `rgvarg` layout, and semantic mapping to callback parameters are not recovered. Therefore a client may expose `OnDataChanged` by that exact name and accept a late-bound call, but must not promise payload ordering or count beyond the TypeLib contract.

### Typed call shape and delivery join

The `MakeCB` slice contains a direct virtual call through slot `+0x1c` at old `0x10013ad2` / new `0x10013bdc`; this is statically consistent with the declared typed `OnDataChanged` slot. It is not evidence that the receiver is specifically the `pCB` argument, nor that a given request reaches the call. The separate `IDispatch::Invoke`-shaped call at old `0x100146a0` / new `0x100147aa` uses slot `+0x18`. Thus both a typed-call shape and a late-bound dispatch-call shape exist in the static slices; they must not be conflated, and neither closes request-to-delivery provenance.

The exact edge from a specific async transaction/completion owner to the callback helper is **UNRESOLVED**. In the new build, a Flush-region path at `0x100134ab` conditionally calls helper `0x100139c2` when owner `[this+0x28]` has bit `0x80000`; no equivalent old cyclic caller was verified. This proves only one guarded route to a general dispatch candidate, not that every subscription reaches `OnDataChanged`.

Accordingly, client-facing language may state that the TypeLib declares typed `OnDataChanged` and the static `MakeCB` slices contain both a typed-slot `+0x1c` call shape and a separate `IDispatch::Invoke` `+0x18` shape. Do not claim that the binary proves runtime delivery, that either receiver is a particular registration argument, that every request invokes `OnDataChanged`, or that delivery is synchronous, ordered, or thread-affine.

## Completion, removal, and shutdown

Use only the public API operation appropriate to the known operation type. Async completion callback is observable through the callback interfaces, but the precise request-to-completion/output-value chain and callback timing are not proven here. Keep request bookkeeping until the client observes its applicable terminal signal; then mark retired and ignore duplicate/late signals safely. This is client-side defensive behavior, not a claim that duplicates occur. Do not free output storage, callback objects, or associated buffers until no in-flight call/callback can access them; exact retention and ownership rules remain unknown, so use conservative lifetime extension and COM reference management.

`RemoveCyclicVariables` is the public cyclic-removal operation (IVar slot 12; IVar2 slot 12). Treat it as a request to remove matching cyclic variables, not proof that a subscription is synchronously stopped, that every item matched, or that callbacks have drained. Keep subscription state and callback resources alive until removal returns and the client has an application-level quiescence rule; the binary evidence does not establish a drain barrier, per-item result, or rollback behavior. Retain the original subscription identity/handle association for retries only if the API contract permits them; that behavior is unresolved. Do not pass an async ReqID to cyclic removal or vice versa.

For shutdown/release, stop initiating work, request removal of known cyclic subscriptions, keep callback/output state alive while outstanding calls or callbacks may still arrive, then release COM references and client storage only after the host application's chosen quiescence condition. No evidence proves that releasing the COM object cancels/drains operations, that removal is synchronous, or that a particular order guarantees safety. A client requiring a hard shutdown barrier must obtain a separate documented/runtime contract; do not claim one from these binaries.

### Client identity, correlation, and late signals

Treat `ReqID` as an opaque value returned through the public output parameter only when the call/result contract and runtime validation establish that it was actually written. Preserve its exact representation; associate it with the owning COM instance, interface revision, operation kind, and client generation in the collector registry. Never use a transaction pointer, `pReqID` storage address, diagnostic scalar, or `CCyclicID` object as a substitute. If output is missing or ambiguous, mark identity unavailable and do not attempt ID-based removal.

Keep the submitted `ClientHandles` mapping per operation/subscription, including duplicate handles and duplicate requested variables. At callback ingress, validate each VARIANT and its bounds/type before interpreting it. Correlate an item by `ClientHandles` only if target validation confirms the callback handle representation and matching semantics; until then preserve the raw callback payload and mark item correlation unresolved. Do not silently zip arrays by position or discard unmatched entries.

Store method HRESULT, per-item `pErrors`, callback `Errors`, quality, timestamp, and value as distinct observations. Missing optional callback fields are “not supplied,” not success or zero. Preserve quality/error/freshness separately from last-good value. Store timestamp payload and its raw type/value without inventing UTC, source, or acquisition-time semantics. Do not treat a successful method HRESULT as per-item success.

Callbacks can race submission return, removal, and shutdown from the client's perspective; this is a defensive race model, not a claim that the vendor delivers them. Make dispatch nonblocking and idempotent. Associate ingress with a client generation/token; atomically reject or quarantine callbacks for retired generations, duplicate terminal notifications, and callbacks after stop, without dereferencing freed request storage. Do not release callback objects or callback-visible state merely because local state has changed to `Terminal` or a removal call returned. The host must define and test its quiescence rule; absent a proven drain barrier, no finite wait can be represented as vendor-guaranteed quiescence.

### COM hosting safeguards

The binaries do not establish apartment model, callback thread, or message-pump requirements. As a conservative host policy, initialize COM on the chosen owner thread, create/use/release the interface there, and serialize collector state transitions. Choose STA or MTA only to match the hosting application and validate it on the target PCU. If STA is used, provide the host's required message dispatch while waiting; never block the only callback/message-dispatch path waiting for that same callback. If a callback arrives on another thread, marshal/copy validated data into collector-owned state and do not make recursive COM calls from the callback. These are deadlock/lifetime safeguards, not vendor threading guarantees; if the host cannot meet them, prefer the synchronous path.

### Synchronous fallback

Until async/cyclic behavior is validated on the deployment, use the historically runtime-proven synchronous batched `ReadVar` path for production collection. Bound call duration at the host level, surface HRESULT and per-item errors separately, and keep last-good values with explicit freshness. A timeout around a blocking COM call does not cancel it; do not release its buffers or interface while the call may still be executing. Async/cyclic may be enabled only after target-PCU validation of interface availability, callback route/payload, item mapping, apartment/pump behavior, error handling, and removal/late-callback lifecycle.

## Exact static evidence and unresolved transitions

| Claim | Static anchor | Status / limit |
|---|---|---|
| Public async/cyclic/remove entrypoints and slots | canonical `MCVAR_CLIENT_CONTRACT.md` and `MCVAR_COM_ABI.json` | Vtable map; not runtime execution. |
| Async output pointer stored at transaction `+0x98`; returned transaction pointer separately wrapped at `+0x04` | `stages/stage16_7/reqid/REQID_LIFECYCLE.md` lines 14-16, 23 | Direct instruction dataflow. |
| `+0x20` scalar reaches RID formatter, but output identity is not proven | same file lines 16, 33, 37 | Producer/key/output connection unresolved. |
| Transaction ID constructor/list cleanup machinery exists, but async insertion/lookup chain is absent | same file lines 25-33, 39 | No ReqID-keyed lookup proof; do not infer cleanup linkage. |
| Cyclic object lifecycle is distinct | same file line 41; `evidence/ghidra_new_iter2_xrefs.txt` lines 48-53 | Symbol/function evidence; no cross-namespace equivalence. |
| `StartCyclics` input validation and helper calls | `evidence/new_internal_read_raw.txt` lines 879-941; old counterpart `evidence/old_cyclic_public_raw.txt` lines 7-52 | Public flow shown; this slice does not establish actual subscription insertion/removal completion. |
| Remove entry target and internal helper references | `evidence/ghidra_new_iter2_xrefs.txt` lines 53, 30-32; `evidence/old_vtable_ctor_xrefs.txt` strings at lines 15-18, 59-73 | Address/name evidence; exact removal effects and completion barrier unresolved. |
| Field-offset scan is candidate-use inventory only | `reqid/iter2_field_use_scan.json` lines 1-2 | Cannot assign semantic ownership from offset matches alone. |

Open transitions that must remain unresolved: async submission to numeric ID production and output write; request registration to lookup; completion/cancel/wait/free/delete/destruction per-request chain; cyclic ID production to `StartCyclics` insertion; cyclic remove to per-record deletion and callback quiescence; shutdown/release to cancellation or drain. Evidence provenance and expanded limitations are in `stages/stage16_7/reqid/REQID_LIFECYCLE.md` and `stages/stage16_7/evidence`.
