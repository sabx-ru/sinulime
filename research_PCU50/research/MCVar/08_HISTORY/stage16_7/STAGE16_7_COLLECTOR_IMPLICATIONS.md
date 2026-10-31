# Stage 16.7 Collector Implications from Corrected Evidence

## Scope and status

This note translates corrected Stage 16.6 and Stage 16.7 offline findings into conservative implications for a future acquisition contract. It is architecture research only. It specifies no collector, COM client, callback sink, scheduler, Windows tooling, DDE/NCDDE, or runtime behavior. Static evidence does not establish operational support. Runtime capabilities remain gated on evidence from the exact intended deployment.

Evidence labels follow Stage 16.6: **STATIC_PROVEN** is a byte-, instruction-, or TypeLib-level fact; **STATIC_INFERRED** is a constrained interpretation; **SAFEGUARD** is a conservative design rule; **RUNTIME GATE** is a deployment test required before enablement; **UNKNOWN** remains unresolved. Historical runtime evidence applies only to its recorded PCU/host/build/case.

## Newly relevant static edges

- **Entry and transaction start (STATIC_PROVEN):** Corrected entry candidates for `ReadVarAsync` directly call the shared transaction starter in both images. The legacy overlapping labels are not independent forwarding-thunk evidence. A future contract may distinguish method invocation from later request/result processing, but must not infer a runtime async guarantee from this entry path.
- **Request ID and result publication (STATIC_PROVEN / UNKNOWN):** The caller's `pReqID` pointer is stored in transaction offset `+0x98`; this is a pointer, not the generated numeric ID. A separate result helper writes through an output pointer. The generated scalar's source, when/how the caller observes a value, transaction-specific registration or lookup, and ordering relative to method return remain unresolved. Contract fields must keep invocation return, output-ID observation, completion/result, timeout, cancellation, and cleanup as distinct events. A nonempty ID is not completion or proof of successful registration.
- **Callback dispatch (STATIC_PROVEN callsites / UNKNOWN linkage):** The `+0x14` call resolves `OnDataChanged` with `IDispatch::GetIDsOfNames`; it is not delivery. A separate callback routine contains an `Invoke`-shaped `+0x18` call and nearby diagnostics, but no proven edge ties it to a particular async/cyclic request. Actual callback execution, successful HRESULT, argument packing, callback-object lifetime, and thread/apartment are unknown. A future contract may record observed dispatch kind and callback receipt, but must represent callback absence/timeout and unknown dispatch path without manufacturing a completion.
- **Cyclic flush/helper (STATIC_PROVEN local edge / UNKNOWN scheduler):** Both images contain FlushCyclics-region list/object accesses. The new image has a conditional direct call from that region to helper `0x100139c2`, guarded by owner bit `0x80000`; helper diagnostics support a general callback-dispatch role. This does not prove that this call delivers `OnDataChanged`, that old build has the same caller edge, or that DataChange/IdleCB schedules the flush. Do not model a proven periodic scheduler, change-only stream, or complete data-change-to-callback chain.

These edges refine where a future contract should place observations; they do not close any async or cyclic runtime gate.

## Contract implications

1. **Keep the synchronous baseline separate.** Preserved historical PCU logs prove synchronous batched `ReadVar` only in their tested context. This remains the only evidence-backed baseline, subject to exact-deployment identity and ABI verification. Do not substitute async/cyclic based on static declarations or callsites.
2. **Represent observations, not inferred internals.** Capture request start, method return/HRESULT, observed output parameters, returned positions/items, callback receipt if it actually occurs, and local timestamps as separate facts. Preserve source timestamps separately. For async/cyclic, record vendor IDs only when observed, with their source and observation time; do not promise ID timing, uniqueness, lookup scope, or completion semantics.
3. **Preserve shape and uncertainty.** Keep input position and identity, duplicates, optional/missing callback metadata, per-item status, and outer HRESULT distinct. A callback not observed by a configured deadline is a timeout/no-callback observation, not a fabricated failed or completed transaction. Preserve raw requested/revised rates and deadband/critical inputs; units, normalization, filtering, and cadence are unresolved.
4. **Do not expose speculative scheduling controls as semantics.** The contract may carry requested configuration and observed delivery timestamps, but must not promise recurring delivery, cadence, server freshness, deadband behavior, or scheduler ownership until measured. A local scheduler used by an eventual collector would be a separate implementation policy, not an inference from `IdleCB`/`FlushCyclics` names.
5. **Keep lifecycle handling gated.** Do not assume callback retention/AddRef, apartment marshaling, safe cancellation, removal behavior, or no callbacks after removal. Contract state should allow late callbacks and unresolved cleanup until target runtime tests establish ordering and ownership.
6. **Preserve provenance and capability status.** Every acquisition record should identify exact DLL/TypeLib hashes, OS/PCU/provider, architecture, acquisition mode, and the gate result. Static capability inventory and runtime-enabled capability must be separate fields or concepts.

## Runtime gates before enabling async or cyclic

No Stage 16.7 static result enables either capability. For the exact intended deployment:

- Verify DLL/TypeLib identity and Windows `ITypeInfo` ABI, including method order, parameter flags/types, references, and vtable layout.
- Establish COM object creation, owning STA/apartment, message-pump requirements, reentrancy, callback execution thread/apartment, and object/callback lifetime.
- For async, demonstrate actual `ReadVarAsync` return versus output-ID publication and completion timing; prove which typed or `IDispatch` path is used, inspect actual callback arguments and HRESULT, and test timeout/no-callback, error, cancellation races, late callback, shutdown, and release.
- For cyclic, observe creation, first and steady delivery, requested/revised-rate meaning and cadence, unchanged/change/quality cases, deadband and critical-value behavior, suspend/resume, removal/cancel races, disconnect/reconnect, and absence or handling of post-removal callbacks.
- Retain raw observations and set target-specific latency, timeout, failure, and resource acceptance criteria. Passing async gates does not enable cyclic, or vice versa.

Until applicable gates pass, async and cyclic remain unavailable; use only the separately verified synchronous baseline. This note does not claim that baseline is universally compatible or operational without its own exact-deployment checks.

## Evidence and unresolved items

Primary basis: Stage 16.6 `architecture/COLLECTOR_REQUIREMENTS.md`, `async/ASYNC_REQUEST_LIFECYCLE.md`, `corrections/dispatch/ASYNC_CALLBACK_DISPATCH.md`, `cyclic/CYCLIC_LIFECYCLE.md`, `algorithms/RATE_AND_FILTER_ALGORITHMS.md`, `reports/EVIDENCE_LEDGER.json`, and `reports/OPEN_QUESTIONS.md`.

Still unknown: per-request reachability to `Invoke`, actual callback success and arguments, generated ReqID source and transaction lookup, callback ownership/threading, cyclic scheduler and causal chain, removal/cancel terminal behavior, and rate/deadband/critical semantics. No Windows runtime experiment or implementation was performed for this note.
