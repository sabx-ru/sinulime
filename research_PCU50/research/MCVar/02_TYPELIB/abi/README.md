# Stage16.5 Async/Cyclic TypeLib ABI

## Result

Offline revalidation of the Stage16 decoder output found eight target TypeInfos in both snapshots: `IVar`, `IVar2`, `IReadVarAsyncCallback`, `IWriteVarAsyncCallback`, `IReadVarAsyncCallback2`, `IWriteVarAsyncCallback2`, `IMCCommand`, and `IMCCommandAsyncCallback`. All eight normalized decoded records are byte-for-byte equivalent as JSON structures between `old` and `new`; no changed paths were found. `IVar` and `IVar2` are separate interface revisions, not old/new versions of one interface. The JSON preserves every decoded type-info field, with method/parameter descriptors, flags, memids, calling convention and custom-data retained.

## Key ABI facts

- `IVar` and `IVar2` each expose 12 methods with the same memids 1-12: `ReadVar`, `WriteVar`, `ReadVarAsync`, `WriteVarAsync`, `ReadVarCyclic`, `RemoveCyclicVariables`, `LookupVariables`, `Cancel`, `Suspend`, `Resume`, `Remove`, `CalculateRequestRates`.
- `Cancel`, `Suspend`, and `Resume` each take one required input `VT_I4 ReqID`. `CalculateRequestRates` takes input `VT_VARIANT RequestedUpdateRates` and outputs `VT_VARIANT* pRevisedUpdateRates` on both interfaces.
- `IVar.ReadVarCyclic` uses input `Names: VT_VARIANT`, in/out `pServerHandles: VT_VARIANT*`, `ClientHandles: VT_VARIANT`, callback pointer `IReadVarAsyncCallback*`, `pDisp: VT_DISPATCH`, `Deadbands` and `RequestedUpdateRates: VT_VARIANT`, output `RevisedUpdateRates: VT_VARIANT*`, in/out `pReqID: VT_I4*`, optional output `pErrors: VT_VARIANT*`, optional `CriticalValues: VT_VARIANT`.
- `IVar2.ReadVarCyclic` uses the same ordering/memid but `Names` and `ServerHandles` are optional input variants, callback pointer type is `IReadVarAsyncCallback2*`, revised rate parameter is named `pRevisedUpdateRates`, and remaining parameters/flags are preserved exactly in the machine record.
- `IVar.RemoveCyclicVariables` takes `ReqID`, `Names`, `ServerHandles`, optional output `pErrors`; `IVar2` additionally has optional input `ClientHandles`.
- Legacy read callback `OnDataChanged` takes required `Values`, `Qualities`, `ClientHandles`; callback2 takes required `Values`, `TimeStamps`, `ClientHandles`, optional `Qualities`, `ServerInfos`, `Errors`. Legacy write callback `OnWriteComplete` takes required `Qualities`, `ClientHandles`; callback2 takes required `ClientHandles`, optional `Errors`.
- `IMCCommand.ExecuteAsync` has input `Command: VT_VARIANT`, `Cookie: VT_I4`, `IMCCommandAsyncCallback* pCB`, `VT_DISPATCH pDisp`, and output `VT_I4* pReqID`. The callback `OnCommandCompleted` takes required `Cookie: VT_I4`, `Error: VT_I4`, `OutArguments: VT_VARIANT`. `IMCCommand.Cancel` takes input `ReqID: VT_I4`.

## Semantic boundary and uncertainties

These are static decoded TypeLib declarations, not observed execution. The data establishes exposed interface IDs, dispatch members/memids, parameter VARIANT descriptors, directions/optionality, and referenced callback interfaces. It does not establish array shape or element interpretation inside VARIANTs, whether a given callback or dispatch sink is invoked, callback order/thread/apartment, request-ID allocation/reuse, synchronous completion possibility, cancellation/suspend/resume effects, cyclic scheduling or update policy, rate units/rounding, removal matching rules, HRESULT/error mapping, or object lifetime. No behavior is inferred from names such as `CriticalValues`, `Deadbands`, `CalculateRequestRates`, `Suspend`, or `Cancel`.

The source Stage16 report itself identifies the parser model as not independently validated against Windows `ITypeInfo` and records runtime questions. Supporting PE string extracts are corroborative strings only and are not used to assign semantics. No Windows executables or collector were built or run.

## Evidence and artifacts

- Authoritative input: `/root/PL/stages/stage16/reports/typelib_decode.json` (`old` and `new`).
- Static decoded source notes: `/root/PL/stages/stage16/reports/STAGE16_TYPELIB.md`.
- Existing semantic/runtime open questions: `/root/PL/stages/stage16/reports/OPEN_QUESTIONS.md`.
- PE string evidence (corroborative only): `/root/PL/stages/stage16_5/evidence/rizin_old_async_cyclic_strings.txt`, `/root/PL/stages/stage16_5/evidence/rizin_new_async_cyclic_strings.txt`.
- Full machine-readable exact normalized records: `typelib_abi_records.json`.
- Machine-readable old/new comparison: `typelib_abi_comparison.json`.
- Reproducible offline extraction/comparison: `build_abi_records.py`.

Re-run with `python3 /root/PL/stages/stage16_5/abi/build_abi_records.py`.
