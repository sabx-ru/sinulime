# Stage 16.7 Old/New Cross-Version Comparison

## Scope and result

Offline static comparison of the remaining P0 paths: IVar2 vtable/interface, callback dispatch, ReqID handling, and cyclic request paths. **No material behavioral difference is established from the available artifacts.** This is an evidence limitation, not a finding of equivalence.

No old/new target binaries or function-level disassembly/CFGs are present in this stage workspace. The available evidence consists of `evidence/old_target_strings.txt`, `evidence/new_target_strings.txt`, and the respective PE section summaries in `old_method_pointer_search.txt` and `new_method_pointer_search.txt`.

## Evidence

- The old/new target string inventories have the same 54 entries in the same order. IVar2/IVar method labels for `ReadVarAsync`, `ReadVarCyclic`, `RemoveCyclicVariables`, and `CalculateRequestRates` are textually the same; addresses shift by a consistent image-layout offset. Callback log strings for `OnWriteComplete` and `OnDataChanged` (Dispatch and Dual variants) and their ReqId formatting also match. Evidence: `evidence/old_target_strings.txt` and `evidence/new_target_strings.txt`.
- Interface/resource labels match, including `IVar2 Read-Callback Interface`, `IVar2 Write-Callback Interface`, `IReadVarAsyncCallback`, and method names for the cyclic operations. These resource strings establish labels only; they do not establish vtable slot contents or call targets.
- PE section summaries show the old `.text` raw/virtual size as `0x2b000`, new as `0x2c000`; the following sections are correspondingly shifted by `0x1000` in virtual/physical layout. This is compatible with an image layout/size change but does not identify whether code in any target function changed.
- The provided method-pointer-search files contain only PE section summaries, not pointer matches, vtable entries, or xrefs. No normalized code bytes or CFG is available to compare.

## Path-by-path status

| Path | Static result | Evidence limitation |
|---|---|---|
| IVar2 vtable/interface | No difference established | Names/resources match; no vtable data, slot targets, or function bytes available. |
| Callback dispatch | No difference established | Callback log strings match; no dispatch implementation, interface slot, argument setup, or HRESULT flow available. |
| ReqID handling | No difference established | ReqId log format and cyclic method labels match; no assignment, propagation, width/conversion, lookup, or removal code available. |
| Cyclic read/removal | No difference established | Method/resource labels match; no subscription state transitions, request construction, cancellation, or cleanup CFG available. |

## Conclusion

There is **no static evidence here to claim a compatibility regression**, and equally no basis to claim these code paths are equivalent. The only observed structural difference is the `.text` section size (+`0x1000`) and downstream section shift; without the binaries this cannot be attributed to the P0 paths. A defensible semantic comparison requires both target images (or matched function disassemblies with addresses/relocations normalized) and vtable/xref data. No runtime, Windows, collector, or DDE testing was performed or used.
