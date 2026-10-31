# MCVar API Reference

## Static COM identity

Both preserved PE32/i386 builds contain embedded ATL registration and a TypeLib resource named `Sinumerik HMI MCVar 1.0 Type Library`.

- CLSID: `{8F64C6F2-C2A4-11D2-BFCA-00609792C500}`
- ProgIDs: `MCVar.Var2`, `MCVar.Var2.1`
- Aliases mapped to the same embedded CLSID: `MCVar.Var`, `MCVar.Var.1`, `MCVar.MCCommand`, `MCVar.MCCommand.1`
- TypeLib: `{8F64C6E3-C2A4-11D2-BFCA-00609792C500}`
- Threading model: `Apartment`
- Trace class: `{DEB5BB92-C585-11D2-BFCF-000000000000}`, threading model `Both`
- Exports: `DllCanUnloadNow`, `DllGetClassObject`, `DllRegisterServer`, `DllUnregisterServer`

Evidence: `RAW_EVIDENCE/old_REGISTRY_101_1033.bin`, `new_REGISTRY_101_1033.bin`, `old_TYPELIB_1_1033.bin`, `new_TYPELIB_1_1033.bin`, `mcvar_pe_resource_inventory.json`.

## Named surface

The embedded TypeLib/decorated symbol evidence names `ReadVar`, `WriteVar`, `ReadVarAsync`, `WriteVarAsync`, `ReadVarCyclic`, `RemoveCyclicVariables`, `LookupVariables`, command methods (`Cancel`, `Suspend`, `Resume`, `Remove`, `CalculateRequestRates`, `Execute`, `ExecuteAsync`), trace methods (`Print`, `GetDebugFlags`, `SetDebugFlags`) and callback method names (`OnDataChanged`, `OnWriteComplete`, `OnCommandCompleted`).

These are **PROVEN_STATIC_NAME_ONLY**. Exact IIDs, DISPIDs, Automation VARTYPEs, `[in]/[out]` directions, optionality and SAFEARRAY declarations are not promoted without a type-info decode or live COM observation. Write/execute/debug-setting methods were never invoked.

## ReadVar

Previous saved Windows runtime evidence establishes tested cases for scalar BSTR and `SAFEARRAY(BSTR)`, output arrays preserving positions, per-item errors, mixed item errors with outer `S_OK`, invalid array shape `0x80070057`, and CacheDevice values 0/1/2. This is a tested-case contract, not a universal signature or freshness guarantee.

## Async/events

Callback names and async/cyclic method names do not establish native event delivery. No `IConnectionPointContainer`/`Advise` runtime enumeration or source-interface metadata was proven. See `SUBSCRIPTION_CAPABILITIES.md`.

## Version scope

Old: 2004-06-23, SHA-256 `43a5c199...e7d98712`.
New: 2011-07-25, SHA-256 `5e7d955e...4428c24`.
Both registration resources are byte-identical, but TypeLib resource hashes differ. Never transfer old VAs to the new image.
