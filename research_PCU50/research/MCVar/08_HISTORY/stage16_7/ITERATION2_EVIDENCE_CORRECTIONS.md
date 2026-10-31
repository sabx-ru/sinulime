# Stage 16.7 Iteration 2: Entry and Scheduler Corrections

This additive correction supersedes the Stage 16.7 first-pass descriptions that treated `0x1000d28a` / `0x1000d39c` as COM slot-9 targets. They are interior/shared-body entry candidates, not the actual vtable entries.

## Verified COM targets

Exact source binaries:

- Old: `/root/PL/PCU_old/H/mmc2/MCVar.dll`, SHA-256 `43a5c1991d98b6b6e155233a0114d7ff72bf4dec7edf58d0607da501e7d98712`, image base `0x10000000`.
- New: `/root/PL/PCU_new/C/RECYCLER/S-1-5-21-4025392478-4199590385-3038547483-1005/Dc28/files/F/mmc2/MCVar.dll`, SHA-256 `5e7d955ebe7cfd52424b04e91471b7408f42bf6cc427e3d94c50bc7f4428c24a`, image base `0x10000000`.

COFF ATL vftable symbol names and `.rdata` bytes establish these table addresses:

| Image | Interface | Vftable VA | slot 9 ReadVarAsync | slot 11 ReadVarCyclic | slot 12 RemoveCyclicVariables |
|---|---|---:|---:|---:|---:|
| Old | IVar | `0x1002c5e4` | `0x1000c3f6` | `0x1000faf0` | `0x10010bbb` |
| Old | IVar2 | `0x1002c630` | `0x1000c28a` | `0x1000f93e` | `0x10010a94` |
| New | IVar | `0x1002d5f4` | `0x1000c508` | `0x1000fc02` | `0x10010ccd` |
| New | IVar2 | `0x1002d640` | `0x1000c39c` | `0x1000fa50` | `0x10010ba6` |

The tables begin with ATL interface-specific `IUnknown`/`IDispatch` implementations, then the interface methods. The pointer values are read directly from the `.rdata` table bytes and resolve into `.text`. `verify_vtables.py` checks all 12 targets from original binary bytes; result: `PASS`.

The four target bodies are directly named in COFF symbols and match the table slot pointers. `ReadVarCyclic` bodies terminate with `ret 0x40` (callback2 signature) or `ret 0x3c` (callback1 signature), independently confirming the ABI variants. `RemoveCyclicVariables` entries are separate for IVar and IVar2 revisions.

## Scheduler evidence correction

Decorated COFF symbols exist for old/new `CVarThreadState::CBOnIdle`, `CCyclicID::DataChange`, `CCyclicID::IdleCB`, and `CCyclicID::FlushCyclics`. Exact addresses are version-specific:

| Method | Old VA | New VA |
|---|---:|---:|
| `CBOnIdle` | `0x10011a20` | `0x10011b32` |
| `DataChange` symbol | `0x10011b4c` | `0x10011c5e` |
| `IdleCB` | `0x10012c01` | `0x10012d13` |
| `FlushCyclics` symbol | `0x10012d7f` | `0x10012e91` |

`CCyclicID` vftable data at old `0x1002c980` / new `0x1002d990` has slot 1 target `IdleCB` at old `0x10012c01` / new `0x10012d13`. This proves the virtual target identity for the `CCyclicID` virtual function table.

The `CBOnIdle` body contains indirect callbacks through saved registers (`call edi`, `call esi`) while walking callback records, but the disassembly slice does not yet prove those registers resolve to `CCyclicID::IdleCB` for a specific list item. The `DataChange` COFF symbol at old `0x10011b4c` is a real object-code symbol but the containing region has overlapping/misaligned downstream symbols and is not treated as a valid independent body boundary without additional control-flow ownership. `FlushCyclics` also has malformed symbol start bytes. The new direct conditional call at `0x100134ab -> 0x100139c2` remains verified only as a local edge from the containing processing region to `CRequestID::MakeCB`, not as proof of an IdleCB-driven callback for a given subscription.

## Remaining unresolved edges

- `ReadVarAsync` request transaction -> callback helper -> successful `IDispatch::Invoke` for that request.
- Numeric async ReqID generation, registration insertion, lookup-key comparison, and exact completion/cancel cleanup.
- `CCyclic::Data` -> valid `DataChange` body -> pending/idle registration -> `CBOnIdle` item -> virtual `IdleCB` -> `FlushCyclics` -> a specific callback.
- Exact COM object construction/interface-subobject pointer assignment from ATL creator/QueryInterface to these vtable addresses.
- Runtime callback success, apartment/thread, scheduling cadence, and hardware behavior.

No Windows, PCU, DDE, collector, or live runtime was used. Primary raw files are `old_ivar_vtable_raw.txt`, `old_ivar2_vtable_raw.txt`, `new_ivar_vtable_raw.txt`, `new_ivar2_vtable_raw.txt`, `old_target_disassembly.txt`, `new_target_disassembly.txt`, the Ghidra xref exports, and `cyclic/*objdump.txt`.
