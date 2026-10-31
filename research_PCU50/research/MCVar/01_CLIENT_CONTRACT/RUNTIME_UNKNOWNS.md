# Runtime Unknowns

## Cyclic configuration and delivery

The following remain unknown from the preserved TypeLib, offline raw public-body fragments, and available cyclic evidence. Do not turn API names, `VARIANT` types, or isolated code paths into client-side behavioral guarantees.

- **Rate semantics:** units/time base of `RequestedUpdateRates`; accepted numeric types/ranges; zero/negative handling; normalization, clamp, rounding, aggregation, and meaning of `pRevisedUpdateRates`/`RevisedUpdateRates`; default when omitted or malformed.
- **Deadbands and critical values:** input value units, accepted representation, comparison/filter algorithm, per-item mapping, defaults, and any interaction between `Deadbands` and optional `CriticalValues`.
- **SAFEARRAY contract:** whether SAFEARRAY is required; element VARTYPE, rank, bounds/lower bounds, emptiness, scalar acceptance/broadcasting, matching-length requirements, and validation/error behavior for all cyclic `VARIANT` configuration and output parameters.
- **Handles and errors:** `ClientHandles` shape/order/matching rules; output `Errors` layout and defaults; whether registration partially succeeds on an item error.
- **Quality changes:** whether quality can change independently of value and trigger delivery; quality codes, provenance and filtering behavior. Callback2 exposes optional `Qualities` output, but this alone does not settle these behaviors.
- **Timestamps:** `TimeStamps` output availability, meaning, source and default. No guaranteed source timestamp is established by static public-body evidence.
- **Cadence and callback:** actual cyclic cadence, scheduling mechanism, coalescing, callback invocation/delivery guarantees, and end-to-end `DataChange`/pending/idle/flush chain. The new image has a conditional flush-region helper edge, but callback identity and old-build equivalence remain unresolved.
- **Registration lifecycle:** exact list insertion, selection precedence, rollback, removal matching, unlink/free behavior, and owner lifetime after final removal.
- **Runtime ABI/behavior:** no Windows `ITypeInfo` oracle or exact-deployment runtime validation was performed; decoded TypeLib records establish encoded declarations, not operational acceptance or runtime semantics.

## Callback registration and delivery blockers

These blockers are specific to the MakeCB slices and public async/cyclic entrypoint evidence. They prevent stronger client-facing promises.

- **`pCB` versus `pDisp`:** the TypeLib declares both inputs and the starter directly stores pointer-like values at transaction `+0x84`, `+0x88`, and `+0x90`, but no unique use identifies which field is which. Do not expose those offsets or hard-code a mapping.
- **Request-to-helper join:** `ReadVarAsync -> starter -> retained values` is direct, and the helper contains the dispatch-shaped route, but a specific transaction/completion owner to helper edge is unresolved. Callback delivery for every request is therefore not proven.
- **Typed versus late-bound call shapes:** no typed *delivery* to a uniquely identified registered `pCB` was established, but the MakeCB slices do contain a virtual call through slot `+0x1c` at old `0x10013ad2` / new `0x10013bdc`. Since slots 0-6 are IUnknown/IDispatch, `+0x1c` is consistent with the first interface-specific typed callback method (`OnDataChanged`). Separately, `GetIDsOfNames("OnDataChanged")` is direct at old `0x1000fef1` / new `0x10010003`, and `IDispatch::Invoke`-shaped calls through slot `+0x18` are direct at old `0x100146a0` / new `0x100147aa`. These are distinct call shapes; which route a particular request uses, if any, remains unresolved.
- **`[ecx+0x1c]` receiver identity:** the vtable call shape is direct and typed-slot consistent, but the receiver loaded from `[ebx+0x10]` is not mapped to `pCB`, `pDisp`, or a particular request. Successful invocation and runtime delivery are not proven. The DISPID-like local belongs to the separate Invoke-shaped path, not evidence that the `+0x1c` call is Invoke.
- **Invoke payload:** six 16-byte-looking copy blocks and `pDispParams = &var_28h` are visible; `cArgs`, `cNamedArgs`, `rgvarg` ordering, and semantic VARIANT mapping are not recovered. Do not promise callback payload order from these bytes.
- **Threading and timing:** callback thread, apartment, ordering, re-entrancy, retry, coalescing, and callback HRESULT effects are not established.
- **Retention and release:** pointer-like retention stores and release/cancellation diagnostics exist, but exact AddRef/Release ownership, counts, receiver-specific retention, and per-request cleanup order are not proven. Clients must retain callback/dispatch objects through their own quiescence rule.
- **Cyclic route:** new `0x100134ab -> 0x100139c2` is a guarded direct Flush-region edge when owner `[this+0x28]` bit `0x80000` is set. It does not prove subscription identity, final `OnDataChanged` delivery, or old-build equivalence.
- **Removal drain:** `RemoveCyclicVariables` exists, but remove-to-delete/free and callback-drain barriers are unresolved. Do not release resources immediately merely because removal returned.
- **Request identity:** `pReqID` pointer storage at transaction `+0x98`, the result-wrapper transaction pointer at `+0x04`, and a separate `+0x20` scalar/RID diagnostic must remain distinct. Numeric ID production, registration, lookup, and output-write linkage are unresolved.

## Evidence required to close these blockers

1. A Windows COM harness implementing both typed callback interfaces and an `IDispatch` object that records `QueryInterface`, `AddRef`, `Release`, thread/apartment, DISPID, `DISPPARAMS`, counts, named arguments, VARIANT types, HRESULT, and callback order.
2. Controlled async and cyclic calls with distinct sentinel `pCB` and `pDisp` objects, followed by completion, cancel, remove, release, late-delivery, duplicate-delivery, and callback-error cases.
3. Complete native tracing or bounded data-flow closure joining each public request to the helper and identifying retained-field mapping; run separately against old and new images.

Until these artifacts exist, use the conservative registration/lifetime rules in `CALLBACK_AND_LIFECYCLE.md` and label delivery, payload, threading, and release semantics as unresolved.

Evidence: `stages/stage16/reports/STAGE16_TYPELIB.md`; `stages/stage16/reports/typelib_decode.json`; `stages/stage16_7/callbacks/CALLBACK_PROVENANCE.md`; `stages/stage16_7/callbacks/CALLBACK_DISPATCH_GRAPH.json`; `stages/stage16_7/callbacks/CALLBACK_ARGUMENT_LAYOUT.json`; `stages/stage16_7/callbacks/old_makecb_exact.txt`; `stages/stage16_7/callbacks/new_makecb_exact.txt`; `stages/stage16_7/entrypoints/iter2`; `stages/stage16_7/rates/RATE_FILTER_FINDINGS.md`; `stages/stage16_7/cyclic/CYCLIC_REGISTRATION_TRACE.md`; `stages/stage16_7/cyclic/CYCLIC_SCHEDULER.md`; `stages/stage16_7/cyclic/CYCLIC_SCHEDULER_XREF_EVIDENCE.md`; `stages/stage16_7/reports/OPEN_QUESTIONS.md`.
