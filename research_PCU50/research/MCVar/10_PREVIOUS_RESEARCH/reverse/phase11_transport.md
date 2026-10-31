# MCVar-to-NCDDE Transport Architecture: Static Reconstruction

## Scope and conclusion

Read-only static inspection of the preserved old `MCVar.dll`, relocated/new `MCVar.dll`, and existing `ncdde.exe` disassembly artifacts. No binary was patched, no vendor process was run, and no live DDE exchange was observed. VA is preferred below; for MCVar (image base `0x10000000`), RVA = VA - `0x10000000`. For `ncdde.exe`, VAs are image addresses as shown by its existing disassembly (base `0x00400000`).

**Conclusion:** MCVar is demonstrably a classic USER32 window-message DDE client/server component, not a DDEML client: its imports include `PostMessageA`, `SendMessageA`, DDE LPARAM pack/unpack/reuse/free routines, and no `DdeInitialize`/`DdeClientTransaction` imports. Its code contains a `CDdeAction::StartRequest` implementation candidate and an explicit `WM_DDE_REQUEST` message path. Separately, `ncdde.exe` has DDEML callbacks and a binary `DdeCreateDataHandle` producer/serializer. These establish two sides of a plausible architecture, but the specific causal chain from this `CVar2::ReadVar` invocation through a particular `CDdeAction` to an `ncdde.exe` request/response remains unproven. The smallest exact MCVar-side unresolved instruction boundary is in `CVar2::ReadVar` at old callsite `0x1000BD47` (RVA `0xBD47`) into helper `0x1000C532` (RVA `0xC532`); the downstream USER32 message call has not been recovered from that execution chain.

## Binary identity and relocation

| Image | Evidence | Key locations |
|---|---|---|
| Old MCVar | PE32 i386; base `0x10000000`; `MCVar.dll` under `PCU_old/H/mmc2` | `ReadVar` body `0x1000BC30`; the export/symbol label `0x1000BC74` is interior code, not the entry |
| New MCVar | PE32 i386; base `0x10000000`; compiled 2011-07-25 versus old 2004-06-23 | matching symbols relocated: StartRequest `0x10004B35`, constructor `0x1000E156`, MakeCB `0x100149C2`; `ReadVar` symbol is relocated from the old body and visible alias `0x1000BD86` in prior evidence |

New/old differences are not uniform: e.g. ReadVar downstream helper is old `0x1000C532`, new `0x1000C644`; request lifecycle helper `0x10014CBE` / `0x10014DC8`. Use symbol identity and instruction comparison, not one blanket delta. `rz-bin -s` resolves old/new `StartRequest`, `StartPoke`, `GetNcddeBinaryData`, `PostMess`, `CRequestID` constructor, and `MakeCB` symbols. Symbol names aid interpretation but are not sufficient proof of execution.

## Observed MCVar graph

### ReadVar and its helper

Old `CVar2::ReadVar` body begins `0x1000BC30` (RVA `0xBC30`); symbol alias `0x1000BC74` is inside it. Existing raw flow documents validation/copy and preparation of stack VARIANT-like records. At `0x1000BD47`:

```asm
1000BD39  lea eax,[ebp-0x2c]
1000BD3C  mov ecx,ebx
1000BD3E  push eax
1000BD3F  lea eax,[ebp-0x2c]
1000BD42  push eax
1000BD43  lea eax,[ebp-0x2c]
1000BD46  push eax
1000BD47  call 1000C532
```

`0x1000C532` begins `push ebp; mov ebp,esp; sub esp,0xe8`, saves `this` from `ECX` at `[EBP-4]`, initializes local state and calls helpers including `0x1000CE2B`, `0x10007E2F`, and `0x10008A8E`. Rizin lists multiple callers (`0x1000AE2E`, `0x1000B737`, `0x1000BD47`, etc.), so its demangled `AddNcddeErrorInfo` attribution is not a sufficient semantic identification for every use. The bytes/call establish entry into a substantial request/error preparation routine, not message submission.

At `0x1000BDDC`, ReadVar calls `0x10014CBE`. Existing phase evidence resolves this as cleanup/lifetime: restore linked state and call an attached object's vtable slot `+8`. It is not a submit edge. Therefore `ReadVar -> 0x10014CBE` must not be represented as `ReadVar -> StartRequest`.

### CRequestID constructor and MakeCB

Old constructor symbol is `0x1000E044` (RVA `0xE044`); new equivalent is `0x1000E156` (RVA `0xE156`). The constructor queries interfaces and, on a bounded branch, creates/copies a SAFEARRAY via imported `SafeArrayCopyData`: old bytes at `0x1000E076-0x1000E07C` push `8`, `0`, `0x11`, then call IAT `0x1002C1B8`. New uses IAT `0x1002D1B8` at `0x1000E18E`. This confirms request-ID initialization/data-copy behavior, not DDE submission.

Old `CRequestID::MakeCB` symbol at `0x100148B8` begins in the middle of an instruction (`03 10`); the true instruction decoding starts earlier. Its body includes a conversion call at old `0x10014968 -> 0x10006DA3` (`CXVariant::Set` by symbol), followed by logging and indirect object dispatch, including `call [ecx+0x1C]` at `0x10014A00`. New equivalent symbol is `0x100149C2`, also interior/misaligned; its code has corresponding `CXVariant::Set` at `0x10014A72 -> 0x10006E25` and slot `+0x1C` call at `0x10014B0A`. Signature names the output as `CDdeAction **` and six `VARIANT *`, strong semantic intent evidence. The observed MakeCB body alone does not establish which concrete CDdeAction object is passed or whether a synchronous DDE transaction occurs.

### DDE action and message path evidence

Old symbols resolve `CDdeAction::StartRequest` at `0x10004AF6` (RVA `0x4AF6`), `StartPoke` at `0x10004C2A`, `CXVariant::GetNcddeBinaryData` at `0x10004DF3`, and `CDdeCon::PostMess` at `0x1000676F`. However, the raw bytes at `0x10004AF6` are incompatible with a valid function prologue (`10 85 C0 75 15 ...`), while the coherent preceding code starts at `0x10004AC8`. The symbol/function boundaries in this area overlap. Thus the label is a locator, not reliable function-entry proof; do not cite the apparent call list in this region without decoding its true CFG.

The old `0x10004C2A` label also overlaps output of the same recovery issue. A nearby coherent path at `0x10004BC2` pushes `0`, `ESI`, `0x3E8`, then calls `0x1000576F`; afterward it handles the returned value and possibly stores it at `[EDI+0x28]`. This is not yet proven to be the `StartRequest` message submission.

MCVar imports USER32 functions: `PostMessageA` IAT `0x1002C240` (new `0x1002D240`), `SendMessageA` `0x1002C22C` (new `0x1002D22C`), `PackDDElParam` `0x1002C224`, `UnpackDDElParam` `0x1002C228`, `ReuseDDElParam` `0x1002C220`, `FreeDDElParam` `0x1002C234`, plus window creation/message-loop APIs. It imports no DDEML functions. Strings contain `WM_DDE_REQUEST`, `WM_DDE_DATA`, `WM_DDE_ACK`, `WM_DDE_INITIATE`, `ncdde`, `ncddeBinary`, `NcddeMachineName`, `NcddeServiceName`, and `CDdeCon::PostMess` / `CDdeAction::StartRequest` diagnostics. This combination gives **high confidence** MCVar implements a USER32 DDE transport generally. It does **not** prove that this ReadVar instance reaches any one import call.

`CDdeCon::PostMess`'s import-call xref and exact parameters were not independently recovered in this pass. Thus the precise message handoff site, target HWND and concrete message/value for ReadVar are still unresolved.

## Independent ncdde evidence

Existing `MCVAR_REQUEST_CHAIN.md` and raw artifacts establish old `ncdde.exe` DDEML and response-side machinery. They identify `DdeInitializeA` at `0x421041` with callback `0x401983`, service registration via `DdeNameService` at `0x4211C7`, callback dispatcher `0x420B20`, and a request dispatcher at `0x448AC0`. Its format branching includes text, a registered binary format, and OEM text; normal request path reaches object producer helpers and the recovered serializer `0x44A730` then `0x44AD50 -> 0x44AE23 -> DdeCreateDataHandle`. A separate callback transaction case `0x2022` calls `DdeCreateDataHandle` at `0x420C4A`; this is not identified as the response to the `XTYP_REQUEST=0x20B0` route. The distinctions matter: existence of a DDEML request responder and a binary serializer does not prove linkage to a particular MCVar ReadVar call.

`ncdde.exe` VAs use base `0x00400000`; its MCVar peer's USER32 classic DDE protocol and `ncdde`/`ncddeBinary` names make cross-process window DDE a practical architectural hypothesis. No static dataflow from MCVar `ReadVar` arguments to an `ncdde.exe` request item or from a correlated request message to the serializer buffer has been established.

## Competing transport hypotheses

| Hypothesis | Supporting evidence | Contradictions / missing proof | Assessment |
|---|---|---|---|
| H1: ReadVar uses classic USER32 `WM_DDE_REQUEST` to ncdde; ncdde answers through DDEML and binary serializer | MCVar imports USER32 DDE parameter/message APIs, has WM_DDE string set and `StartRequest`; ncdde exposes DDEML callback, request dispatcher and `DdeCreateDataHandle` serializer | no ReadVar-to-PostMess call chain; no target HWND/item/formats trace; ncdde `XTYP_REQUEST` callsite-to-normal serializer edge and cross-process correlated object/buffer absent | **Most plausible overall architecture (medium)**; causal invocation chain **unproven** |
| H2: ReadVar uses USER32 DDE but obtains a different ncdde response path (e.g. callback-side handler, not normal serializer) | multiple ncdde callback transaction cases, including a separate `0x2022` handle writer; MCVar message architecture fits | transaction type `0x2022` is not `XTYP_REQUEST`; no request correlation or item mapping | **Possible (low-medium)** |
| H3: ReadVar transport is COM/local callback or another helper, and DDE components serve other APIs/operations | COM interfaces, CRequestID/MakeCB, and local callback code exist; `ReadVar` also has COM-facing behavior | USER32 DDE infrastructure and specific request naming strongly indicate DDE is an intended transport at component level | **Possible for this invocation/branch (low-medium)**; no direct transport edge recovered |
| H4: `0x10004E2E` is the transport call | instruction is indirect virtual call near mislabelled StartRequest/GetNcdde region | resolved vtable `0x1002C3A0 + 4 -> 0x100010D6`, bytes `C2 04 00` (`ret 4`); local result slot, not transport | **Rejected (high confidence)** |

## Exact unresolved instruction boundary

There are two distinct boundaries; do not conflate them:

1. **ReadVar request-processing boundary:** old callsite `0x1000BD47` (RVA `0xBD47`) direct call to helper `0x1000C532` (RVA `0xC532`). New relocated callsite is reported at `0x1000BE59` to `0x1000C644` in the new xref/caller output. The callee is substantive and may construct downstream operation state, but the exact next operation that submits or posts is unresolved. This is the **smallest actionable boundary** to continue.
2. **Nearby result-slot false lead:** old `0x10004E2E` (RVA `0x4E2E`) executes `call [edx+4]`; with vptr `0x1002C3A0`, slot `+4` is `0x100010D6`, whose raw bytes are `C2 04 00` (`ret 4`). This is a no-op virtual result operation; it is not a DDE/API edge. The complete local bytes are preserved in `FUNCTIONS/mcvar_10004e2e_resolution.asm`.

## Proposed causal graph (confidence on each edge)

```text
Automation caller
  --[high, interface/symbol and observed test invocation; not tied to server packet]--> CVar2::ReadVar
  --[high, direct call 0x1000BD47 -> 0x1000C532]--> ReadVar request/error-preparation helper
  --[UNRESOLVED, exact next submission instruction not identified]--> MCVar DDE action/connection
  --[medium, component-level architecture only: USER32 DDE imports + WM_DDE_REQUEST strings]--> classic USER32 window-message DDE path
  --[medium, ncdde-side registration/dispatch evidence]--> ncdde DDEML callback/request dispatcher
  --[high within ncdde only, recovered static calls]--> serializer / DdeCreateDataHandle response path
```

Additional supported but unjoined edges:

```text
CRequestID constructor --[high, direct calls/field writes]--> request-ID state and SAFEARRAY copy
CRequestID::MakeCB --[high, direct conversion + vtable-slot calls]--> callback/action-oriented state preparation
CVar2::ReadVar --[high, direct call]--> 0x10014CBE cleanup helper --[high, vtable slot +8]--> lifetime/release operation
```

Do not draw `MakeCB -> concrete CDdeAction instance`, `ReadVar -> StartRequest`, `ReadVar -> PostMessageA`, or `MCVar buffer -> ncdde serializer` as solid edges. Cross-module architecture is compelling at the subsystem level, not at invocation-causality level.

## Confidence and remaining work

- **High:** PE identity and old/new symbols/relocations; ReadVar direct call into `0x1000C532`; `0x10014CBE` cleanup semantics; `0x10004E2E` resolves to `ret 4` for the identified vtable; USER32 classic DDE API imports; independent ncdde DDEML callback and serializer calls.
- **Medium:** MCVar component intended to communicate with ncdde using classic window-message DDE; CRequestID/MakeCB represents part of request/callback object lifecycle.
- **Low/unproven:** which concrete operation and data from the specific ReadVar reaches DDE; whether `StartRequest` executes for it; which HWND/item/format/message is used; whether response uses normal ncdde serializer versus another route; exact cross-process payload/buffer correspondence.

Highest-value next static slice: decode `0x1000C532` with accurate function boundaries and follow every branch to a direct call or vtable operation, then trace the concrete object allocation/vptr installation. Separately recover `CDdeCon::PostMess` body and xrefs, particularly the exact `PostMessageA` argument setup, and tie its callsite to the ReadVar flow. On ncdde, resolve `0x448AC0` normal request branch back to the actual `XTYP_REQUEST` transaction case. Runtime causality would require instruction/object/message or packet correlation; none is claimed here.

## Sources

- Existing accepted: `research/MCVAR_REQUEST_CHAIN.md`, `research/phase11/FUNCTIONS/mcvar_transport_boundary.md`, `research/phase11/FUNCTIONS/mcvar_10004e2e_resolution.asm`.
- ReadVar raw flow: `research/logs_asmb/phase9_mcvar_readvar_focus.asm`.
- Other existing evidence: `research/phase11/FUNCTIONS/mcvar_readvar_request_transport.md`, `research/logs_asmb/62_rizin_request_bridge_raw.txt`, `research/logs_asmb/64_objdump_request_callers_raw.txt`, `research/logs_asmb/68_consolidated_request_trace_raw.txt`, `research/logs_asmb/79_objdump_dde_imports_raw.txt`, `research/logs_asmb/87_real_request_448ac0_449a80_raw.txt`.
- Fresh read-only inspection: `rz-bin -I/-i/-s`, `rz-bin -zz`, Rizin `pdf`, and GNU `objdump -d` on old and relocated/new MCVar binaries.
