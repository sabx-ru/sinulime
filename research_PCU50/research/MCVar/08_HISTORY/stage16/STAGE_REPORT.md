# Stage 16: MSFT TypeLib Recovery

## Result

Both preserved MCVar TypeLib resources were decoded offline with pinned `pycomtypelib==0.1.0`. The decoder produced 28 TypeInfos for each resource and identical target TypeInfo records for `IVar`, `IVar2`, and the async callback interfaces.

The recovered static contract includes exact decoded GUIDs, dual/Automation flags, `memid`, `CC_STDCALL`, HRESULT return descriptors, parameter order, `PARAMFLAG` direction/optional bits, recursive pointer/user-defined descriptors and vtable byte offsets (`oVft`). The normalized target summary is in `evidence/async_cyclic_abi_summary.json`; the full parser output is in `reports/typelib_decode.json`.

Notable IVar2 records:

- `ReadVarAsync`: callback pointer `IReadVarAsyncCallback2*`, output request ID, optional output errors.
- `ReadVarCyclic`: callback pointer, deadbands, requested update rates, revised update rates output, in/out request ID, optional critical values and errors.
- `RemoveCyclicVariables`: request ID plus optional names/server handles/client handles and optional output errors.
- `IReadVarAsyncCallback2::OnDataChanged`: values, timestamps, client handles, optional qualities/server infos/errors.

## Verification

```text
/root/PL/stages/stage16/typelib/.venv/bin/python -m pytest /root/PL/stages/stage16/typelib -q
2 passed in 0.27s
```

The tests explicitly assert target memids, vtable byte offsets, calling convention, HRESULT returns, callback parameter order and command callback presence. The decoder was rerun with explicit input environment variables; regenerated JSON is byte-identical to the checked-in artifact (SHA-256 `4a12d51556ff8df856033074a15cc5990e98bc3b85721ef30acdbfb72d37ff9c`).

Rizin independently confirms `TYPELIB/1/1033` resources at the expected offsets and 19.3 KiB size in both exact DLLs. Resource hashes match the Stage 15 and preserved research evidence.

## Boundary

This is strong encoding-decoded static evidence, not a Windows `LoadTypeLibEx` oracle. No Windows COM runtime or PCU was available. Therefore this stage does not prove method invocation, nonblocking behavior, callback delivery, connection points, message pumping, callback thread, cyclic persistence, unsubscribe behavior, reconnect semantics, or resource cleanup. No write-capable method was invoked.

The next stage must validate the decoded contract against Windows `ITypeInfo` and then perform bounded read-only runtime experiments on the exact authorized PCU build. Until then the production collector remains polling-backed and native async/cyclic remains capability-gated.
