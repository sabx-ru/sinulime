# Phase 9: MCVar request-object/vtable boundary

## Scope

Offline static recovery only. Inputs are the old `PCU_old/H/mmc2/MCVar.dll` and `ncdde.exe`; no vendor execution, live DDE, SHA/vendor access, or runtime object capture was used.

## Recovered call/object mapping

| Evidence | Observation | Strength |
|---|---|---|
| `MCVar.dll: 0x1000BC74` | Old `CVar2::ReadVar` initializes output VARIANT state, prepares local VARIANT/header/error state, then directly calls `0x10014CBE` at `0x1000BDDC`. | solid |
| `MCVar.dll: 0x10014CBE` | Rizin and objdump agree on a function boundary: `mov esi,ecx`; load `[esi+4]`; if non-null, load linked object `[+0x28]`, call `0x10014CE7`, reload `[esi+4]`, copy `[esi]` to linked object `[+0x24]`; then invoke linked-object vtable slot `+8` (`call [eax+8]`) with the linked object as argument. | solid |
| `MCVar.dll: 0x10014CE7` | Decrements `[object+0x4c]`, evaluates state, and may post message `0x401` using the linked object/window context. This is lifecycle/notification processing, not serializer construction. | solid |
| `MCVar.dll: 0x1000E044` | Exported symbol identifies `CRequestID::constructor(CVar2*, IUnknown*, IDispatch*, unsigned long)`. The body immediately performs COM `QueryInterface`-shaped preparation and initializes request-related state; exact complete constructor boundary is affected by adjacent overlapping symbols. | solid identity; partial body |
| `MCVar.dll: 0x100148B8` | Exported symbol identifies `CRequestID::MakeCB(unsigned long, CDdeAction**, VARIANT*, VARIANT*, VARIANT*, VARIANT*, VARIANT*, VARIANT*)`. Its recovered body calls `CXVariant::Set` on `NCDDE_BINARY_HEADER`-typed data, then dispatches through an object vtable at slots `+0x14`, `+0x18`, and `+0x1c` depending on branches. | solid identity and indirect operations |
| `MCVar.dll: 0x10014CBE` label | It is not a constructor and is not `StartRequest`; it is a `CRequestID` lifecycle/propagation helper. The earlier generic “request-construction helper” label is narrowed accordingly. | solid correction |
| old `StartRequest` label `0x10004AF6` | Raw bytes at the label are not a valid prologue; usable bytes begin around `0x10004AC8`. No direct `ReadVar -> StartRequest` call was recovered. | dashed semantic candidate |
| old request-region vcall around `0x10004E1D` | A real indirect dispatch through `[esi]` vtable `+4` exists, but the object’s allocation, concrete vtable address, and target are unresolved. | solid operation; dashed identity/target |

## Causal interpretation

The strongest old MCVar chain is:

```text
CVar2::ReadVar 0x1000BC74
  -> CRequestID lifecycle helper 0x10014CBE                 [solid]
  -> linked request object via [this+4]                    [solid field flow]
  -> linked object vtable slot +8                          [solid indirect call]
  -> CRequestID::MakeCB typed request/VARIANT interface    [dashed as runtime relation]
  -> CDdeAction / DDE request machinery                    [dashed; no direct xref]
```

`CRequestID` is the recovered MCVar-side identity connecting `CVar2` inputs to a request-oriented interface. `MakeCB`’s type signature and binary-header conversion establish a strong semantic relation to DDE request data, but do not establish that the same object is the `CDdeAction` instance at the overlapping `StartRequest` label.

The ncdde side remains independently proven:

```text
ncdde request dispatcher 0x448AC0/0x449265
  -> object/producer path 0x449301...
  -> per-item serializer 0x44A730
  -> final DDE handle path 0x44AD50 -> 0x44AE23 -> DdeCreateDataHandle
```

No static call, shared vtable address, shared allocation site, shared buffer pointer, or cross-module interface identifier joins the MCVar `CRequestID`/`CDdeAction` objects to the ncdde serializer objects. Therefore the MCVar-to-ncdde object identity and buffer/data-flow edges remain dashed.

## New vs old

The new image has relocated identities reported as `ReadVar 0x1000BD86` and `MakeCB/request-related target 0x10014DC8`, but a complete new constructor/vtable disassembly was not recovered in this phase. The old object mapping must not be projected onto the new image beyond those reported equivalent labels.

## Evidence files and commands

- `research/functions/old_readvar_flow.rz`
- `research/functions/old_mcvar_disasm_0x4ac8.txt`
- `research/logs_asmb/phase9_serializer_44a730_44ad50_raw.asm`
- GNU `objdump -Mintel -D` on `MCVar.dll` ranges `0x1000BC30..0x1000BE10`, `0x1000E044`, `0x100148B8..0x10014E26`
- Rizin `aaa; pdf/axt` on `MCVar.dll` at `0x10014CBE`, `0x1000E044`, and `0x100148B8`
