# MCVar Client Contract

## Activation evidence

The original MCVar PE resource inventory records the TypeLib resource as `TYPELIB/1/1033`, LIBID `{8F64C6E3-C2A4-11D2-BFCA-00609792C500}`, and embedded registration strings. The prior resource reconstruction records CLSID `{8F64C6F2-C2A4-11D2-BFCA-00609792C500}` with ProgIDs `MCVar.Var2[.1]`, `MCVar.Var[.1]`, and `MCVar.MCCommand[.1]`; the Var and MCCommand names are aliases in embedded registration data mapping to one CLSID, not proof of distinct coclasses. This resource evidence establishes names/identifier association, not successful activation on any deployment. The final contract does not claim a runtime activation result. Source: `/root/PL/stages/stage15/evidence/COM_API_REFERENCE.json` and `/root/PL/stages/stage15/evidence/pe_resource_inventory.json`.

## Canonical COM ABI

The complete ordered signatures, IIDs, flags, slots, and version-specific target VAs are in [MCVAR_COM_ABI.json](MCVAR_COM_ABI.json). `memid` is the Automation DISPID; it is distinct from the native vtable slot. The requested interface methods are `CC_STDCALL`, declared `FUNC_PUREVIRTUAL` with HRESULT return. Canonical static slots: `ReadVarAsync` 9, `ReadVarCyclic` 11, `RemoveCyclicVariables` 12. Verified vtable words are checked by `verification/verify_final_package.py` and the source vtable verifier.

The callback declarations are also in the ABI JSON. Callback1 `OnDataChanged(Values, Qualities, ClientHandles)` has three required `[in] VT_VARIANT` parameters. Callback2 `OnDataChanged(Values, TimeStamps, ClientHandles, Qualities?, ServerInfos?, Errors?)` has three required and three optional `[in] VT_VARIANT` parameters. The IVar/IVar2-to-callback mapping is declared in TypeLib. The evidence does not prove which callback route is used at runtime.

`ReadVarAsync.pReqID` is `[out] VT_I4*`; `ReadVarCyclic.pReqID` is `[in,out] VT_I4*`. Do not infer initialization requirements or ID-generation semantics from the direction flag. For precise flags on all methods and old/new revisions, use the JSON as the canonical ABI.

## Client-side ABI use policy

- Construct the interface/coclass using registration values observed on the target deployment. The embedded TypeLib/resource records associate LIBID `{8F64C6E3-C2A4-11D2-BFCA-00609792C500}`, CLSID `{8F64C6F2-C2A4-11D2-BFCA-00609792C500}`, and ProgIDs `MCVar.Var2[.1]`, `MCVar.Var[.1]`, `MCVar.MCCommand[.1]`; this is static registration metadata, not proof activation succeeds on a given PCU.
- Select IVar or IVar2 by successful `QueryInterface` on the deployed COM object, not by software version alone. The selected interface determines the callback interface and removal signature.
- Treat `VARIANT` values as opaque Automation values until runtime validation establishes whether they contain SAFEARRAYs, element type, rank, bounds and ownership. Initialize output variants deliberately and clear only values owned by the client according to COM Automation rules.
- Preserve HRESULT separately from per-item errors and quality. The TypeLib signature does not establish that successful HRESULT means all requested items succeeded.

## Cyclic configuration (public surface only)

### `ReadVarCyclic`

The preserved TypeLib declares `IVar::ReadVarCyclic` and `IVar2::ReadVarCyclic` as `FUNC_PUREVIRTUAL`, `CC_STDCALL`, returning HRESULT at the COM ABI boundary. The `memid` is the dispatch ID (DISPID), not the HRESULT. These signatures expose configuration as `VARIANT` parameters; this describes the COM surface, not a guaranteed SAFEARRAY element type or validation policy. Old and new decoded TypeInfo signatures match.

| Parameter | TypeLib type and flags | Client-facing fact |
|---|---|---|
| `RequestedUpdateRates` | `VARIANT`, `[in]` | Input configuration value; units, legal range, normalization, clamping and default are unknown. |
| `pRevisedUpdateRates` (`IVar2`) / `RevisedUpdateRates` (`IVar`) | pointer to `VARIANT`, `[out]` | Output slot for a revised-rate value. Meaning, units and relationship to the request are unknown. |
| `Deadbands` | `VARIANT`, `[in]` | Input configuration value; units, comparison rule and default are unknown. |
| `CriticalValues` | `VARIANT`, `[in, optional]` | Optional input configuration value; interpretation and default are unknown. |
| `ClientHandles` | `VARIANT`, `[in]` | Input accompanying cyclic registration; accepted shape and correspondence rules are unknown. |
| `pErrors` | pointer to `VARIANT`, `[out, optional]` | Optional output; per-item layout and error/default behavior are unknown. |

In `IVar2`, `Names` and `ServerHandles` are optional input `VARIANT`s; `IVar` instead declares required input `Names` and in/out `pServerHandles`. These are signature differences only and do not define array shape or validation.

### Array and output limits

The TypeLib says these parameters are `VARIANT`, not `SAFEARRAY` descriptors. Static public signatures alone do not establish whether a caller must pass a SAFEARRAY, which rank/bounds are accepted, element types, empty-array behavior, scalar broadcasting, or whether arrays must have matching lengths. Treat all such rules as unknown. No client should infer defaults or repair malformed input based solely on parameter names.

`Qualities` and `TimeStamps` do not appear as `ReadVarCyclic` parameters. `IReadVarAsyncCallback::OnDataChanged` declares `Values`, `Qualities`, and `ClientHandles` as `VT_VARIANT [in]`. `IReadVarAsyncCallback2::OnDataChanged` declares `Values`, `TimeStamps`, and `ClientHandles` as `VT_VARIANT [in]`, followed by optional `Qualities`, `ServerInfos`, and `Errors`, each `VT_VARIANT [in, optional]`. These are callback method inputs from the callback object's perspective, not `[out]` pointers. This proves the declared callback ABI only; it does not establish delivery, content, quality codes, timestamp source, or runtime defaults.

### Cyclic operation boundary

Static `ReadVarCyclic` routes directly into the internal reader and that reader calls a `CCyclic` constructor with an owner-relative list argument. This is registration-path evidence, not proof that the constructor inserts the record or that a persistent subscription is successfully established. The `CCyclicID::Delete` target has a vtable entry, but the static evidence does not establish a `RemoveCyclicVariables` call to that target; therefore do not treat it as the remover's internal deletion routine. A flush-region traversal and one new-build conditional helper call are observed, but no complete `DataChange` → pending work → scheduler → flush → callback chain or cyclic cadence is proven.

Evidence: `stages/stage16/reports/STAGE16_TYPELIB.md`; `stages/stage16/reports/typelib_decode.json`; `stages/stage16_7/cyclic/CYCLIC_REGISTRATION_TRACE.md`; `stages/stage16_7/cyclic/CYCLIC_SCHEDULER.md`; `stages/stage16_7/cyclic/CYCLIC_SCHEDULER_XREF_EVIDENCE.md`.
