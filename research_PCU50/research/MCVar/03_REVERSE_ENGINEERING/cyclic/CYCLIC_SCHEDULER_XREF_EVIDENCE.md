# Cyclic Scheduler Xref and Containing-Function Evidence

## Scope

Offline, read-only analysis of the exact old/new `MCVar.dll` binaries recorded in `../reports/EVIDENCE_RECONCILIATION.md`. No Windows execution, DDE interaction, collector, or binary modification. Raw output below was obtained with Rizin 0.10.0 (`aaa`, `axt`, `pd`, `afl`); addresses are preferred VAs. This note distinguishes exact xrefs from automatic labels and does not promote symbol names to proven semantics.

## Candidate label region: validated boundaries and caller evidence

Raw bytes validate a normal x86 frame prologue at old `0x10012b78` (`55 8b ec 81 ec 94 01 00 00 53 56 8b f1...`) and new `0x10012c82` (same byte sequence). Direct caller xrefs:

- Old `0x1000550d: call 0x10012b78`, in the containing routine starting at `0x100054dd`.
- New `0x1000554c: call 0x10012c82`, in the containing routine starting at `0x1000551c`.

The new import/xref output also reports `0x10012716: call 0x100139c2` and the previously established conditional flush-region edge `0x100134ab: call 0x100139c2`. The former is a caller of the callback helper, not an edge to DataChange/IdleCB/Flush.

By contrast, labels at old `0x10012b4c` and new `0x10012c5e` decode as malformed instructions/branches (new begins `0f 81 ce 00 20 00...`; old begins `ff 8b 45 e8...`). The DataChange label region proceeds to epilogues at old `0x10012b75` / new `0x10012c7f`; the valid prologue then starts at old `0x10012b78` / new `0x10012c82`. These bytes plus direct callers validate the latter as callable function starts; they do not validate the preceding DataChange label as a separate function or establish the identity of the caller's object.

At the valid prologue, disassembly starts a large frame (`sub esp,0x194`) and prepares multiple VARIANT-like result temporaries. Disassembly output then shows invalid/misaligned regions and overlapping labels `IdleCB`, `ShowState`, `GetDeadBand`, and `FlushCyclics`. Treat only byte-valid instructions/local blocks as evidence; automatic CFG/function segmentation across this range is not reliable. Rizin `afij`/`pdf` did not produce an accepted independent function CFG for the candidate starts in this analysis. Thus an end-to-end containing-function CFG and return boundary for the Idle/Flush candidate body remain unavailable; this is a precise limitation, not proof the code is unreachable.

## Timer/message imports: PE import and direct xrefs

Both PE import tables include `USER32!SetTimer`, `KillTimer`, `PostMessageA` and `KERNEL32!WaitForSingleObject`. The new image import addresses are `SetTimer 0x1002d238`, `KillTimer 0x1002d248`, `PostMessageA 0x1002d240`, `WaitForSingleObject 0x1002d040`. Old equivalents are `0x1002c238`, `0x1002c248`, `0x1002c240`, `0x1002c040`.

Rizin direct xrefs in the new image:

- `SetTimer`: `0x1000298d` in `fcn.100028bb`; `0x100059a4` in `fcn.10005912`; plus an import-jump thunk. At `0x10005912`, the containing routine has diagnostic `CTimerServer::AddTimer`; it calls `SetTimer(hwnd=[esi+0x24], id=esi, interval=0x64, callback=0x10007f17)` at `0x100059a4`, stores the result at `[esi+0x1c]`, and configures an entry/timer record. Its callers/xrefs are timer framework and variant code; no cyclic owner pointer join was recovered. `0x100028bb` is in a shutdown/showdown path (`CDdeClass::ShowDown` diagnostic), not established as cyclic scheduling.
- `PostMessageA`: `0x100057ee`, `0x1000582b`, `0x10005886` within `fcn.100057ae`; and `0x10014eca` within `fcn.10014e8a`; plus import thunk. `fcn.100057ae` is `CDdeCon::PostMess` (diagnostic) and passes HWND/message/WPARAM/LPARAM to PostMessageA. `fcn.10014e8a` receives a direct call from `0x10014e7b` and posts message `0x401` to `[esi+0x38]`; its block carries `CDdeClass::CBOnLocalMessage` diagnostics. Neither caller was joined to `CCyclicID` or the valid containing function via object-pointer dataflow.
- `KillTimer`: xrefs at `0x100029ed` in trace/showdown cleanup and `0x10002e77` in `String::Set`, plus import thunk. No cyclic owner join.
- `WaitForSingleObject`: xref at `0x100027f5` in `MCVarDDE::TraceObj`; no cyclic owner join.

Old import xrefs show the same categories and offset shift: SetTimer at `0x1000294e` in a shutdown/showdown path and `0x10005965` in timer-related code; PostMessageA in `CDdeCon`/local-message regions; KillTimer in trace/string routines; WaitForSingleObject in `MCVarDDE::TraceObj`. This is not proof no indirect call or dynamically resolved API exists; it only bounds these imported direct xrefs.

## Removal and deletion chain

New `CVar2::RemoveCyclicVariables` direct disassembly at `0x10011c09..0x10011c57` observes a field test/store on `[edi+4]`, assignment of `esi+0x2c`, direct `call 0x100021c9` with `edi`, direct `call 0x10001104` with `&[edi+8]`, and a conditional call to `0x10001673` with `esi`. These establish local field/call behavior only; `edi`/`esi` provenance is not carried to an identified cyclic owner or record in the captured valid CFG.

The named `CCyclicID::Delete(CCyclic*)` label at new `0x1001166e` is not evidence of a removal call. Direct code there branches into other overlapping labels and no verified direct call xref from RemoveCyclicVariables to Delete was found. `axt` over the reliable candidate addresses returned only the direct containing-function callers noted above for old/new prologue starts; no direct xref was found to the malformed DataChange labels. No dataflow was recovered that links RemoveCyclicVariables selection keys through a record unlink to Delete/free or empty-owner destruction. Therefore the removal-to-delete chain remains unresolved.

## Edge verdict

- `CCyclic::Data -> DataChange -> pending -> idle scheduling -> FlushCyclics`: **not proven**. Candidate label boundaries are invalid/overlapping; the direct calls and import xrefs above do not supply a validated object-pointer chain.
- `FlushCyclics region -> callback helper`: **direct conditional, new only**, `0x100134ab -> 0x100139c2`, guarded by owner `[this+0x28]` bit `0x80000`, as previously recorded. It does not establish callback method identity or old-build equivalence.
- Timer/message/event/wait API -> cyclic owner: **not established**. Direct imported API references were inspected; observed timer and message calls belong to timer/DDE helpers without a cyclic owner join.
- `RemoveCyclicVariables -> CCyclicID::Delete -> free`: **not proven**. Removal-side local idle-list-related calls and the named Delete candidate remain disconnected by direct caller/dataflow evidence.

## Reproduction commands

```sh
rizin -q -c 'aaa; axt @ 0x10012b78; axt @ 0x10012c82; axt @ 0x10012b4c; axt @ 0x10012c5e' OLD_OR_NEW_DLL
rizin -q -c 'aaa; axt @ 0x1002d238; axt @ 0x1002d240; axt @ 0x1002d248; axt @ 0x1002d040' NEW_DLL
rizin -q -c 'pd 100 @ 0x10005912; pd 100 @ 0x100057ae; pd 35 @ 0x10014e8a' NEW_DLL
```
