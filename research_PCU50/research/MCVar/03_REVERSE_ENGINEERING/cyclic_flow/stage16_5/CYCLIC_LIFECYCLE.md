# MCVar cyclic subscription lifecycle (offline static map)

## Scope and artifacts

Analyzed the exact `MCVar.dll` files only, without modifying either binary:

- Old: `/root/PL/PCU_old/H/mmc2/MCVar.dll`, PE32/i386, image base `0x10000000`, timestamp 2004-06-23 07:49:30 UTC.
- New: `/root/PL/PCU_new/C/RECYCLER/S-1-5-21-4025392478-4199590385-3038547483-1005/Dc28/files/F/mmc2/MCVar.dll`, PE32/i386, image base `0x10000000`, timestamp 2011-07-25 07:47:15 UTC.

All addresses below are preferred VA, not file offsets. Analysis used PE metadata, embedded strings/decorated symbols, typelib evidence staged in `stage16/evidence/async_cyclic_abi_summary.json`, and Rizin analysis/disassembly. No runtime execution, DDE investigation, or archive modification was performed.

## Evidence-supported lifecycle

1. **Create request/subscription ID.** `CCyclicID` is the request-ID owner: both builds contain decorated `CCyclicID` constructor/destructor and `new/free CCyclicID/ReqID` diagnostics. It stores/associates a `CVar2`, callback interfaces, dispatch sink, and an ID (constructor signature). The exact ID allocation algorithm and counter/reuse policy remain unresolved.
2. **ReadVarCyclic entry and cyclic records.** The type library marks `ReadVarCyclic` as method id 5 (vtable offset 44), taking Names, server handles, client handles, callback/dispatch, Deadbands, RequestedUpdateRates, RevisedUpdateRates, `pReqID`, optional errors, CriticalValues. Implementation has two overloads for old callback and callback2. Each creates a `CCyclic` record, with logged fields including RID, variable name, critical flag, server/client handles, deadband, and requested update rate. `StartCyclics` is a separate internal helper. Its actual iteration/commit behavior is not fully recovered from the decoded listing.
3. **Data/change notification.** `CCyclic::Data` has an explicit `change` argument and ID diagnostic. `CCyclicID::DataChange(int, CCyclic*)` is a real method; diagnostics expose tag, suspended state (`susp`), and pending count (`pend`), as well as change, hotR, and tag. `OnDataChanged` callback dispatch is implemented for IVar/IVar2 and dual/dispatch paths, with HRESULT diagnostics. Thus data changes enter a request-ID-owned callback path, and suspended/pending state participates in it. Whether every change is coalesced, the meaning of `hotR`, and exact callback-array construction are unresolved.
4. **Scheduling/update.** `CCyclicID` inherits/uses `CIdleCBTarget`; `CVarThreadState::CBOnIdle(CIdleCBTarget*)`, `CCyclicID::IdleCB()`, `CCyclicID::FlushCyclics(int)`, and `CCyclicID::Resume()` are named internal routines. The `IdleCB`/`FlushCyclics` diagnostics and data-change state logs support an idle-callback/flush scheduling path. `CalculateRequestRates` reads/writes a variant array and calls `normalizeUpdateRate`; the latter's body contains SAFEARRAY copy/element operations. Exact normalization formula, timer cadence, and which helper installs/rearms a timer are not proven. Both binaries import USER32 `SetTimer`/`KillTimer`, but import presence is not evidence they serve cyclic subscriptions.
5. **Remove per-variable cyclics.** Type library method id 6 (vtable offset 48) is `RemoveCyclicVariables(ReqID, Names, ServerHandles, pErrors)`. `InternalRemoveCyclicVariables` is an internal helper. `CCyclicID::Delete(CCyclic*)`, cyclic destructor/list types, and `free CCyclic` diagnostics establish record deletion/freeing. Log/resource strings include `Invalid ReqID`. This supports request-ID-scoped removal and per-record deletion; exact matching precedence when Names and handles are both supplied, empty-array semantics, and request-ID destruction when its last record disappears remain unresolved.
6. **Suspend/resume/cancel.** Type library methods: `Cancel` id 8, `Suspend` id 9, `Resume` id 10, each accepts `ReqID`. Public implementations exist, and `CCyclicID::Resume()` exists. `DataChange` records `susp` and `pend`; `CCyclicID` destructor diagnostics also log Suspend. This supports a suspended request-ID state and a resume-related pending-work path. It does **not** establish whether Cancel destroys the ID immediately, cancels a lower transaction, clears pending changes, or differs from removing all variables. The Cancel/Suspend/Resume methods have substantial SAFEARRAY processing, but their exact transitions were not safely reconstructed from the disassembler output.

## Version-specific function map

| Routine | Old (2004) VA | New (2011) VA | Evidence / confidence |
|---|---:|---:|---|
| `CVar2::ReadVarCyclic` callback2 overload | `0x1001093e` | `0x10010a50` | Rizin names; body logs/initializes request object and logs new `CCyclic` fields. High for record creation/logged fields; indirect subsequent calls unresolved. |
| `CVar2::ReadVarCyclic` legacy callback overload | `0x10010af0` | `0x10010c02` | Rizin names; overload and parameter layout match typelib. High for method identity, lower for post-validation flow. |
| `CVar2::InternalReadVarCyclic` | `0x10010c68` | not claimed | Old Rizin symbol listing identifies the helper; new helper address deliberately left unconfirmed. |
| `CCyclic::Init` | `0x10011388` | `0x1001149a` | Rizin named function; old/new listings are partially misdecoded. |
| `CCyclicID` constructor | `0x100113ba` | not claimed | Old constructor is named and has a direct ReqID lookup/invalid-ID branch; new address not verified. |
| `CVar2::StartCyclics` | `0x100115f3` | `0x10011705` | Rizin named function and readable prologue; signature includes request ID, name, server handle, rate/deadband/critical arguments, cleanup list, output. |
| `CCyclicID::Delete(CCyclic*)` | `0x1001155c` | not claimed | Old method name confirmed; new address not claimed. Destructor/free diagnostics support deletion, but no complete path xref recovered. |
| `CVar2::RemoveCyclicVariables` full overload | `0x10011a94` | `0x10011ba6` | Rizin names; typelib signature. `InternalRemoveCyclicVariables` old decorated name at `0x1002f14f` string location, not code VA. |
| `CVar2::RemoveCyclicVariables` shorter overload | `0x10011bbb` | `0x10011ccd` | Rizin names. |
| `CVar2::Cancel` | `0x100122f7` | `0x10012409` | Rizin names; typelib id 8. |
| `CVar2::Suspend` | `0x10012459` | `0x1001256b` | Rizin names; typelib id 9; large routine. |
| `CVar2::Resume` | `0x1001250e` | `0x10012620` | Rizin names; typelib id 10. The short body was misdecoded, so do not infer its behavior from that listing. |
| `CVar2::CalculateRequestRates` | `0x10012868` | `0x1001297a` | Rizin names; array transformation loops visible in listings; calls/helper flow partly corrupted. |
| `CVar2::normalizeUpdateRate` | `0x100129a2` | `0x10012ab4` | Rizin names; SAFEARRAY operations visible. Formula unresolved. |
| `CCyclicID::DataChange(int, CCyclic*)` | `0x10012b4c` | `0x10012c5e` | Rizin names; old function body misdecoded, confirmed via decorated symbol and diagnostics only. |
| `CCyclicID::IdleCB()` | `0x10012c01` | not located | Old Rizin names/diagnostic; first listing instruction misdecoded. |
| `CCyclicID::FlushCyclics(int)` | `0x10012d7f` | `0x10012e91` | Rizin names; new body is large and has branches testing state bits at object offsets `+0x28` and arrays at `+0x58/+0x5c`; bit meanings unresolved. |

Address caveat: strings output addresses are file/RVA offsets unless explicitly prefixed by an image base. Symbol addresses in this table are preferred VA. In the new binary, code has a roughly `+0x112` displacement relative to old for many matched routines; this is not a safe global address transform.

## Request-rate evidence

`CalculateRequestRates` has the COM signature `CalculateRequestRates(RequestedUpdateRates, RevisedUpdateRates)` in both typelib and vtable. It iterates SAFEARRAY data, constructs output elements, and invokes `normalizeUpdateRate`. The `ReadVarCyclic` input path accepts RequestedUpdateRates and outputs RevisedUpdateRates; `StartCyclic` diagnostics store `rupd`. This proves rate input/output processing and per-variable stored rates, but not whether revised values are lower bounds, quantized periods, or server negotiated rates. `normalizeUpdateRate` includes array-copy and element insertion logic; scalar conversion/rounding policy was not recovered.

## Explicit unresolved indirect edges

- `ReadVarCyclic` -> request-ID selection/allocation -> `StartCyclics`: constructor and helper exist, but the exact call chain and error rollback are not verified by complete xrefs.
- `StartCyclics` -> `CCyclic::Init` -> cyclic-list insertion: object/list diagnostics support these objects but insertion order and transactional cleanup remain unresolved.
- `CCyclic::Data`/external data arrival -> `CCyclicID::DataChange` -> `IdleCB` -> `FlushCyclics` -> callback dispatch: the named components and state diagnostics support the conceptual path, but direct call edges are not fully recovered.
- Timer setup/rearm/cancel: USER32 timer imports exist; no timer API xref was verified to these routines. Do not characterize the scheduler as a Windows timer.
- Suspend/Resume/Cancel -> exact flag updates or record cleanup: public methods are located, and suspension/pending state appears in diagnostics, but branches are not trustworthy in current disassembly.
- Remove operation -> `Delete`/automatic deletion of empty ID: named deletion helper and destructors exist; direct calls and final-ID behavior are unresolved.

## Verification record

Commands used included `file`, `objdump -p/-h`, `strings -a -t x`, and Rizin `aaa; afl`/`pdf` against both exact binaries. Rizin identified the decorated symbols and both builds' method addresses. Several optimized functions were incorrectly decoded at entry, so this note treats symbol names, typelib signatures, literal diagnostics, and readable instruction excerpts as separate evidence tiers. No dynamic behavior is asserted.