# Track A Second Pass: MCVar Transport Edge

## Result

**Outcome: transport remains unresolved for this specific `ReadVar` invocation.** The focused static pass confirms the accepted old/new entry chain and independently finds genuine message/DDE callsites elsewhere in MCVar and the named Siemens modules. It does **not** establish that old `ReadVar` at `0x1000BD47 -> 0x1000C532`, or new `0x1000BE59 -> 0x1000C644`, reaches any of those APIs or a broker.

The smallest exact unresolved edge is the indirect call through the object pointer's `+0x14` slot: old `0x1000CA30`, new `0x1000CB42`. Static arguments are VARIANT-/string-like and callback-shaped, but the concrete object/vtable and slot target for this invocation are not recovered. This is distinct from the known local call `ReadVar -> helper`, and from the unrelated direct message callsites in MCVar.

## Evidence and method

Read-only disassembly was run against old `MCVar.dll`, new `MCVar.dll`, old `mbdde.exe`, `dhserver.exe`, `ARServer.exe`, `Dhs.exe`, and new `MMCServer.dll`. `rizin` analyzed import xrefs; `objdump` produced supporting module call listings. No binaries or historical reports were changed. Raw outputs are in [`RAW_EVIDENCE/`](/root/PL/research/phase12/RAW_EVIDENCE/).

The helper boundary is consistent with the existing Phase 12 Track A report: old `0x1000BD47` calls `0x1000C532`; new `0x1000BE59` calls `0x1000C644`. Rizin's helper analysis identifies old `0x1000C532` xrefs including the ReadVar call at `0x1000BD47`; focus logs capture old/new indirect call neighborhoods and the helper's linked-list lookup callee.

The per-item/helper evidence ends in preparatory data handling, local calls, and the unresolved indirect slot. In old/new disassembly the slot call is exactly `call dword [eax+0x14]` at old `0x1000CA30` and new `0x1000CB42`. No direct `PostMessageA`, `SendMessageA`, or DDE API call appears in the recovered helper body. There is no statically recovered slot target, object constructor/vptr provenance, or caller/callee chain joining this slot to the message routines.

## Actual message/DDE callsites found

| Module/image | Static callsite evidence | Meaning/limit |
|---|---|---|
| Old MCVar | `PostMessageA` direct calls at `0x100057AF`, `0x100057EC`, `0x10005847`, and `0x10014DC0`; `SendMessageA` slot/table evidence at `0x10003271` and import thunk | Proves MCVar contains actual message calls elsewhere. No path from this ReadVar helper/slot to these sites is established. |
| Old mbdde | `PostMessageA` calls at `0x43584F`, `0x4399F4`, `0x4414A7`, `0x4419EE`, `0x441D95`, `0x441DD8`, `0x44220D`; many `SendMessageA` calls | Proves message use in mbdde, not that the ReadVar request reaches it. |
| Old dhserver | `PostMessageA` at `0x417C6D`, `0x462B23`, `0x463979`; numerous `SendMessageA` calls | Actual message use, no invocation-specific bridge found in this pass. |
| Old ARServer | `PostMessageA` at `0x404B29`, `0x4240CF`; import thunk | Actual message use, not joined to this MCVar path. |
| Dhs, MMCServer | Import inventory/call scan captured; this pass found no proven callsite tied to `ReadVar` | Dhs is old image; MMCServer is found in new image. Absence in filtered listings is not evidence of no transport. |

MCVar import xrefs and target callsite listings are in `old_mcvar_post_send_xrefs.rz.txt`, `new_mcvar_post_send_xrefs.rz.txt`, and per-module `*_api_xrefs.txt`. Import presence is not used as transport proof. The old module's direct calls demonstrate the message APIs are live code, but they are in different functions and without a recovered call graph from the specific ReadVar object.

## Direct and indirect call/xref resolution

- Directly proven entry edges: old `0x1000BD47 -> 0x1000C532`; new `0x1000BE59 -> 0x1000C644` (existing accepted findings, corroborated by helper disassembly and xref output).
- Helper's downstream object/list lookup: old `0x1000C7C3 -> 0x10014E38`, whose body calls `0x1001968C`; new `0x1000C8D5 -> 0x10014F42`, whose body calls relocated counterpart `0x1001979C`.
- Unresolved indirect edge: old `[eax+0x14]` at `0x1000CA30`; new `[eax+0x14]` at `0x1000CB42`. No concrete vtable is statically established for the object loaded into EAX on this path.
- No recovered direct call from these helper bodies to the old MCVar PostMessage callsites or to `mbdde`, `dhserver`, `ARServer`, `Dhs`, or `MMCServer`.
- The old cleanup relation `0x1000BDDC -> 0x10014CBE` and accepted correction to the old coherent ReadVar body around `0x1000BC30` remain as specified; this report does not reinterpret them as transport.
- Old `0x10004E2E` remains rejected as transport per accepted Phase 11 evidence.

## Reachability verdict

- `ReadVar -> PostMessageA/SendMessageA`: **not proven; not rejected**. The actual API callsites are present in MCVar, but the specific callback slot and its possible indirect targets are unresolved.
- `ReadVar -> DDE API`: **not proven; not rejected** for the same reason. Module DDE imports and callsites alone do not establish execution from this invocation.
- `ReadVar -> broker/module boundary`: **not proven**. No call/jump, vtable target, message payload/target HWND, item identity, or transaction/request-ID join links this invocation to the broker path.

## Minimal dynamic discriminator

On the matching Windows runtime and matching binaries, break immediately before the old call at `MCVar+0xCA30` (new `MCVar+0xCB42`), record `EAX`, read `[EAX]` as the object's vptr and `[vptr+0x14]` as the resolved callee, then single-step/trace that callee until it returns or hits a message/DDE/broker boundary. Set API breakpoints on `USER32!PostMessageA`, `USER32!SendMessageA`, and relevant DDE APIs, recording HWND/message/LPARAM or DDE transaction parameters and stack ancestry. A single `ReadVar` call with one uniquely named item and this call-stack trace discriminates local callback-only handling from actual transport: an observed API/broker call with that ancestry proves reachability; completion without any such call falsifies it for the exercised branch only. If `[eax+0x14]` resolves to a wrapper, continue until the first external/message boundary rather than stopping at the slot.

## Raw evidence index

- `mcvar_mcvar_focus.rz.txt`: old helper disassembly and xrefs.
- `old_mcvar_indirect_edge.txt`, `new_mcvar_indirect_edge.txt`: old/new indirect call and object lookup neighborhoods.
- `old_mcvar_post_send_xrefs.rz.txt`, `new_mcvar_post_send_xrefs.rz.txt`: MCVar API xref output.
- `mbdde_api_xrefs.txt`, `dhserver_api_xrefs.txt`, `ARServer_api_xrefs.txt`, and other `*_api_xrefs.txt`: named module API xrefs.
- `*_imports.rz.txt`: import inventory only, not transport proof.
- `*_calls.txt`: `objdump` filtered call listings; use xref files for classified import callsites.

One Rizin invocation initially used unsupported `axt address` syntax; it was rerun using `s address; axt`. A broad grep-filtered `objdump` output was noisy because it matched decoded symbols/text; findings above rely on the explicit import-xref outputs and the focused instruction slices, not that filter.
