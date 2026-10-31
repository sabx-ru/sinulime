# Collector Integration Requirements

## Scope

This is an implementation specification for a future read-only client. It does not claim that async/cyclic runtime delivery, callback threading, SAFEARRAY shape, or cancellation barriers have been validated on Windows/PCU.

## Interface selection

Use the deployed MCVar COM coclass and obtain the interface actually available on that deployment:

- `IVar` IID `c48394e0-ec79-11d0-99a9-00a0246d1792` uses callback1.
- `IVar2` IID `23ebede0-bd9b-11d1-bd5a-0080c7f7898a` uses callback2.

The complete ordered signatures, IIDs, flags, slots and target VAs are in the canonical root [MCVAR_COM_ABI.json](MCVAR_COM_ABI.json). Redundant duplicate ABI copies were removed from the final package; this root JSON is the sole final source of truth.

## COM ownership and apartment policy

As conservative host policy, initialize COM on the chosen owner thread and create/use/release each interface there; serialize call state and release through that owner. The evidence does not establish STA versus MTA, callback thread, message-pump or reentrancy behavior. Select an apartment to fit the host and validate it on target. If using STA, ensure the host can dispatch messages where required and never block the only dispatch path waiting for a callback. Design defensively for callbacks on another thread: copy/validate payload into collector-owned state and avoid recursive COM calls. These safeguards do not assert vendor thread behavior.

Implement callbacks as independent COM objects with correct `IUnknown` and the selected callback interface. The static MakeCB slices contain a typed-interface call shape at vtable slot `+0x1c` (old `0x10013ad2`, new `0x10013bdc`) as well as a separate `IDispatch::Invoke` call shape at `+0x18` (old `0x100146a0`, new `0x100147aa`). They do not identify either receiver as the registered `pCB` or `pDisp` for a particular request, or prove runtime delivery. Keep strong references to callback and optional dispatch objects from before submission until the client’s quiescence condition after terminal completion/removal. Retain `pReqID` storage and callback-visible memory while deferred access remains possible; method return, terminal state, and removal return alone are not proven drains. This is defensive policy, not a proven vendor AddRef/Release sequence.

## Call preparation

Use exact `CC_STDCALL` parameter order and direction from `MCVAR_COM_ABI.json`. Initialize every input/output VARIANT and output pointer deliberately. Do not infer that a `VT_VARIANT` is a SAFEARRAY: its contained type, rank, bounds, lower bound, element type, empty representation and length matching remain unknown. Validate all returned VARIANTs before consuming them.

For `pReqID`, provide writable initialized storage and preserve it beyond method return until the client has established no deferred write can occur. Treat a value as a ReqID only after output was observed as written under a validated call contract; otherwise mark identity unavailable. Preserve returned bits opaquely; never derive, normalize, or repair an ID.

For callbacks, support both declared shapes:

```text
callback1: Values, Qualities, ClientHandles
callback2: Values, TimeStamps, ClientHandles,
           optional Qualities, ServerInfos, Errors
```

Do not assume callback2 optional values are present, and do not assume array ordering or payload lengths until PCU validation establishes them.

## State and correlation

Maintain separate records keyed by a client-generated operation token, not a vendor ID, for:

- operation kind: async or cyclic;
- owning COM object instance and interface revision;
- client generation/token and operation state;
- submitted input identity and client handles;
- caller output storage address owned by the client;
- opaque ReqID once observed;
- callback/dispatch object references;
- raw callback VARIANTs plus validated per-item values, qualities, timestamp payloads, server information and errors;
- terminal/removal state.

Preserve positional alignment and duplicate variables/handles. Keep method HRESULT, per-item `pErrors`, callback `Errors`, quality, timestamp, and last-good value distinct. Missing optional outputs mean “not supplied,” never implicit success/zero. Do not interpret timestamp units, source, or UTC semantics without target evidence. Correlate by `ClientHandles` only after runtime validation confirms shape and semantics; until then retain raw payload and report correlation unresolved. Do not silently zip by array order, collapse duplicate handles, or discard unmatched items.

Recommended client states:

```text
Submitting -> Pending -> Terminal -> Retired
Submitting -> Failed -> Retired
Pending -> Removing -> Retired
```

These are client states, not claims about Siemens internal states.

## Cyclic operation

Treat `ReadVarCyclic` as capability-gated. Requested rates, revised rates, deadbands, critical values, client handles and optional outputs are declared as VARIANTs, but units, legal ranges, defaults, SAFEARRAY representation and filtering behavior are unresolved. Do not expose an assumed milliseconds contract.

`ReadVarCyclic` declares `pReqID` as `[in,out] VT_I4*`; `RemoveCyclicVariables` declares `ReqID` as `[in] VT_I4`. Static evidence does not establish that `ReadVarCyclic` writes a usable removal key through that pointer, nor the initialization/input semantics for the `[in,out]` parameter. Therefore cyclic removal is capability-gated until the target-release contract documents that mapping or a read-only PCU runtime test verifies it. Do not use an async ReqID, transaction pointer, output-storage address, or guessed/default value. Removal is not established as a synchronous callback-drain barrier; retain callback objects, output storage and subscription state through the application's quiescence policy.

## Shutdown and recovery

1. Stop submitting new operations.
2. Advance the client generation and stop accepting new work. At callback ingress, validate generation/token and atomically quarantine or ignore stale, duplicate-terminal, or post-stop notifications without dereferencing retired operation storage; keep COM callback objects alive.
3. Request `RemoveCyclicVariables` only for subscriptions whose removal key and interface parameter contract are validated on that deployment. Otherwise mark removal unavailable/unresolved and do not fabricate a key.
4. Safely record late/error callbacks for live generations until the client-defined quiescence condition; a deadline is not a vendor-guaranteed drain.
5. Release callback/dispatch references and output storage only after that condition.
6. Release the COM interface on its owner thread.

Because cancellation, disconnect, removal draining and late-callback behavior are unknown, a hard shutdown guarantee cannot be claimed offline. The historically runtime-proven synchronous batched `ReadVar` path remains the production fallback until target-PCU tests validate async/cyclic behavior. A host timeout around synchronous `ReadVar` is not cancellation: preserve call-owned buffers and COM lifetime until the call actually returns.

## Error policy

Preserve method HRESULT separately from per-item `pErrors` and callback `Errors`; keep callback quality and timestamp as independent optional observations. Do not convert missing optional outputs into success, and do not treat a successful method HRESULT as proof that every item succeeded. Retain last-good values independently from quality/error/freshness state and expose freshness explicitly.

## Evidence boundary

Verified static facts: TypeLib declarations, IIDs, `CC_STDCALL`, method slots, target VAs, public calls into `MakeCB`, pointer/scalar distinctions, and the distinct typed `+0x1c` and `IDispatch::Invoke` `+0x18` call shapes documented in the final ABI/lifecycle artifacts. Runtime unknowns: QueryInterface success, which registered argument is the call receiver, request-to-call linkage and callback delivery, SAFEARRAY contract, callback lifetime/threading, AddRef/Release behavior, ReqID lifecycle, cyclic cadence/filtering/removal drain and recovery behavior.
