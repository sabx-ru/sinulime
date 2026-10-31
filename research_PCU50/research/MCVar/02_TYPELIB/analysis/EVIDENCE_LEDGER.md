# Stage 16 Evidence Ledger

| ID | Class | Claim | Evidence | Status |
|---|---|---|---|---|
| S16-01 | STATIC | Old TypeLib resource is 19,732 bytes, SHA-256 `0653a34a342fc6b80e9f675ff9754173b878a353744098e6eb0c9fa429c77bb3`; new is 19,732 bytes, SHA-256 `a7d9968596b9e9a17dff6fc2fcf4a2e2ddc65cedd28dba76eb77791b49dadfd1`. | `evidence/typelib_hashes.sha256`; Stage15 PE resource inventory | CONFIRMED_STATIC |
| S16-02 | STATIC | `pycomtypelib==0.1.0` decodes both resources as `MCVARLib`, GUID `8f64c6e3-c2a4-11d2-bfca-00609792c500`, version 1.0, LCID 1033, 28 TypeInfos. | `reports/typelib_decode.json`; `typelib/requirements.txt`; `reports/STAGE16_TYPELIB.md` | CONFIRMED_ENCODING_DECODED |
| S16-03 | STATIC | `IVar`, `IVar2`, `IReadVarAsyncCallback`, `IReadVarAsyncCallback2`, `IWriteVarAsyncCallback`, and `IWriteVarAsyncCallback2` GUIDs, dual/Automation flags, methods, memids, `CC_STDCALL`, HRESULT returns, parameter flags/types and vtable offsets decode identically in old/new resources. | `evidence/async_cyclic_abi_summary.json`; full JSON | CONFIRMED_ENCODING_DECODED |
| S16-04 | STATIC | IVar2 `ReadVarAsync` uses callback pointer to `IReadVarAsyncCallback2`, output `pReqID`, optional output `pErrors`; `ReadVarCyclic` adds `Deadbands`, `RequestedUpdateRates`, output `pRevisedUpdateRates`, in/out `pReqID`, optional `CriticalValues`; `RemoveCyclicVariables` takes `ReqID`, optional Names/ServerHandles/ClientHandles and optional output errors. | `evidence/async_cyclic_abi_summary.json` | CONFIRMED_ENCODING_DECODED |
| S16-05 | STATIC | Callback2 `OnDataChanged` takes Values, TimeStamps, ClientHandles, optional Qualities, ServerInfos, Errors; legacy callback takes Values, Qualities, ClientHandles. | `evidence/async_cyclic_abi_summary.json` | CONFIRMED_ENCODING_DECODED |
| S16-06 | STATIC | `IMCCommandAsyncCallback.OnCommandCompleted` входит в TypeLib; target record проверяется отдельной regression assertion, без предположений о runtime callback. | `reports/typelib_decode.json`; `typelib/test_decode_typelib.py` | CONFIRMED_ENCODING_DECODED |
| S16-07 | STATIC | Old/new target TypeInfo objects compare equal under the pinned decoder; library-level custom data contains a difference. | `typelib/test_decode_typelib.py`; `reports/typelib_decode.json` | CONFIRMED_ENCODING_DECODED |
| S16-08 | LIMITATION | Decoder output is not an independent Windows `ITypeInfo`/`FUNCDESC` oracle. `stdole2.tlb` imports are resolved by parser model, and no Windows COM runtime was available. | `reports/STAGE16_TYPELIB.md`; `research/MCVar/findings/stage16_typelib_reconstruction.md` | OPEN_VALIDATION |
| S16-09 | LIMITATION | No callback delivery, async nonblocking behavior, cyclic persistence, connection-point behavior, thread identity, reentrancy, cleanup, or PCU runtime semantics are established by this stage. | Stage15 runtime boundary and Stage16 design acceptance criteria | OPEN_RUNTIME |

No write-capable MCVar method was invoked. No PCU was contacted.
