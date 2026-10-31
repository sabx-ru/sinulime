# Stage 16.6: Evidence Correction and Async/Cyclic Reconstruction

## Scope and acceptance boundary

Offline static reverse engineering only. Original `PCU_old`, `PCU_new`, and `research` evidence remained read-only. No Windows executables, PCU packages, collector, mock COM server, web UI, live hardware tests, or DDE/NCDDE work were performed.

## Correction gate

1. `0x1000FEF1` old / `0x10010003` new is classified as `IDispatch::GetIDsOfNames` (`vtable+0x14`), not callback invocation. The argument sequence supplies a zeroed-GUID pointer consistent with `IID_NULL`, one name `OnDataChanged`, LCID `0x800`, and `rgDispId` output.
2. A separate callback routine contains a `+0x18` `IDispatch::Invoke`-shaped call at old `0x100146a0` / new `0x100147aa`; the DISPID-like value is passed from a local populated by the name-resolution path, with nearby `Dispatch "OnDataChanged" called` and returned HRESULT diagnostics. This is static callsite evidence. The exact `DISPPARAMS` semantics, actual callback object success, and per-ReadVarAsync/cyclic reachability remain unresolved.
3. The corrected TypeLib direct-function count is 32 across eight target TypeInfos per revision; the decoded full libraries have 28 TypeInfos and 92 direct function records. The old Stage16.5 count of 33 is an off-by-one reporting error and is explicitly superseded.
4. The canonical boundary record is `corrections/boundaries/corrected_function_map.json`. `ReadVarAsync` entries `0x1000d28a`/`0x1000d39c` are high-confidence entry candidates; contiguous body end is not uniquely assigned because of shared/tail control flow. Legacy labels `0x1000d3f6`/`0x1000d508` are rejected as function entries. DataChange/IdleCB/Flush labels are not accepted as reliable standalone starts.
5. Original Stage16.5 files and raw evidence are preserved unchanged; superseded interpretation history is additive in `corrections/STAGE16_5_CORRECTIONS.md`.

## Static lifecycle findings

### Async request

- Both public entries directly call the shared transaction starter.
- `ReadVarAsync` passes caller `pReqID`; the starter stores that pointer at transaction offset `+0x98`. This is a pointer field, not the generated numeric ReqID.
- A distinct 12-byte result wrapper has a transaction pointer at `+0x04`.
- A downstream completion/result helper writes a value through an output pointer; the exact scalar ReqID generator and transaction-specific lookup/registration edge are not yet proven.
- Completion code contains an interface vtable `+0x14` callsite and transaction-object `+0x04` callsite. A separate callback routine contains an `IDispatch::Invoke`-shaped `+0x18` callsite. The exact path from a particular ReadVarAsync transaction to that Invoke remains unresolved.
- Cancellation/error code can construct an `E_ABORT`-coded record with diagnostic `Com-Object released or Async-Transaction cancelled`; full per-request release order is not established.

### Cyclic acquisition

- Both builds expose cyclic API and internal request/record concepts in TypeLib and implementation diagnostics.
- Raw Flush-region accesses support a list-like owner layout: owner list pointer `this+0x0c`, node next `+0x00`, node object pointer `+0x08`; cyclic object accesses include `+0x38`, `+0x40`, `+0x74`. These are observed offsets, not a complete C++ struct.
- In the new build, a Flush-region path conditionally calls helper `0x100139c2` at `0x100134ab` when bit `0x80000` at `[this+0x28]` is set. That establishes a direct conditional edge to a general callback-dispatch candidate helper only.
- `DataChange -> pending`, `IdleCB -> Flush`, full removal/destruction semantics, old-build equivalent cyclic caller, callback method identity, timer owner and scheduler cadence remain unresolved.

### Rate and filters

- Static interior blocks show byte-mask operations producing 16-bit `0x0000`/`0xffff` values and SAFEARRAY/VARTYPE handling in both versions.
- The rate formula, units, clamp/rounding behavior, Deadbands comparison, CriticalValues semantics and complete algorithm equivalence are not recovered. No pure algorithm regression implementation was added because that would encode unsupported behavior.

## Architecture consequence

Synchronous batched `ReadVar` remains the only `HISTORICAL_RUNTIME_PROVEN` acquisition mode in the preserved PCU logs. Native async and cyclic remain capability-gated. Future collector requirements are in `architecture/COLLECTOR_REQUIREMENTS.md`; no collector code was written.

## Independent review

Final independent Stage16.6 review verdict: **CONDITIONAL PASS**. It reproduced the corrected `GetIDsOfNames` and separate `Invoke`-shaped callsites, the 32/92 TypeLib counts, canonical boundary cautions, JSON/graph closure and PE verifier. Documentation contradictions were corrected. Runtime callback success, per-request reachability, ownership/threading and PCU behavior remain open by design.

## Safety

No PCU was contacted. No write-capable MCVar operation was invoked. No Git was used. DDE/NCDDE remains frozen.
