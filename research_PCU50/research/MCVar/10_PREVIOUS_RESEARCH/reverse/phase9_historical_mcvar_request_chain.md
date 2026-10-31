# MCVar `ReadVar` → request objects → ncdde transport

## Scope and verdict

This note traces the old and relocated/new `MCVar.dll` `CVar2::ReadVar` entry points toward the request/object and ncdde transport code using only the offline instruction logs and recovered evidence under `research/`. It does **not** claim runtime execution, live DDE traffic, or a packet-specific cross-module proof.

**Bottom line:** `ReadVar` is a COM/Automation-facing virtual entry that validates/copies VARIANT and SAFEARRAY inputs, builds local request/error state, and reaches request-construction-labelled code through `0x10014CBE` (old) / `0x10014DC8` (new). The old `StartRequest`/`GetNcddeBinaryData` labels overlap unreliable function boundaries, and the static xrefs do not prove a direct `ReadVar → StartRequest` call. The strongest recovered transport-side path is independently in `ncdde.exe`: callback registration → dispatcher → request/response machinery, plus a recovered serializer path into `0x40203B → 0x44A730` and `0x4012F8 → 0x44AD50 → 0x44AE23 → DdeCreateDataHandle`. The MCVar-to-ncdde join remains dashed.

## Evidence conventions

- **Solid edge:** direct call/thunk/field operation recovered in instruction-level evidence, or a serializer edge explicitly recovered in the current phase.
- **Dashed edge:** indirect COM/vtable dispatch, cross-module object identity, or a semantic join not proven by a call/xref/data-flow chain.
- Addresses are virtual addresses as reported by the logs. “New” means the relocated/equivalent image where the evidence provides the address; it is not an assertion that every helper has a fixed delta.

## 1. Old `CVar2::ReadVar` entry and input/object preparation

Old public virtual entry: **`0x1000BC74`**. New equivalent: **`0x1000BD86`**. The old Rizin flow (`functions/old_readvar_flow.rz`) shows a `__stdcall` Automation-shaped method with VARIANT arguments and a `SAFEARRAY *` argument at stack `+0x14`; it writes/initializes output state and rejects an invalid command-array condition with `0x80070057` / `"Invalid Command Array"`.

The old entry has these observed direct helper calls:

| Callsite | Target | Role supported by evidence |
|---|---:|---|
| `0x1000BC97` | `0x1000AF93` | initial object/argument helper; exact class role unresolved |
| `0x1000BCBA` | `0x1000B7AB` | request/input helper; exact role unresolved |
| `0x1000BCD7` | `0x100017F3` | status/validation helper; return tested against `2` |
| `0x1000BD00` | `0x10009F39` | command/log/error-path helper |
| `0x1000BD10` | `0x10009DAF` | `IMCCommand` execute/error reporting path (format string evidence) |
| `0x1000BD47` | `0x1000C532` | error-info-labelled helper |
| `0x1000BD55` | `0x1000AE8D` | result/status helper |
| `0x1000BD6A` | `0x10007CAF` | decode-error region |
| `0x1000BD76` | `0x10013615` | conversion/result helper |
| `0x1000BD7E` | `0x1000AF73` | result helper |
| `0x1000BDB6` | `0x1000B00B` | element/result conversion helper |
| `0x1000BDDC` | `0x10014CBE` | request-construction-labelled terminal helper |

New evidence identifies the corresponding ReadVar VA as `0x1000BD86`, with representative relocated targets `0x10007DBD` (error), `0x1000C644` (AddNcddeErrorInfo-labelled), and `0x10014DC8` (MakeCB/request-construction-labelled). The body shape is reported as near-identical, but a complete new disassembly/xref listing was not recovered; therefore only those relocated identities are asserted.

### SAFEARRAY and VARIANT branch

The overload at old `0x1000C602` is a second public virtual ReadVar form. It uses:

- `SafeArrayCopyData` with source/destination SAFEARRAYs (one branch pushes `3`, another `8` as the element/command selector);
- `SafeArrayCopy` in the alternate branch;
- `SafeArrayGetElement` in the element loop;
- `VariantCopy` for output/result variants;
- helper `0x10008048` and `0x10007E2F` / `0x10008A8E` in the loop/conversion paths.

This proves that array inputs are copied/iterated and returned through VARIANT objects before request construction. It does **not** prove that the SAFEARRAY memory is the later ncdde packet buffer.

## 2. Request object and indirect dispatch boundary

The request-construction-labelled call `ReadVar → 0x10014CBE` (new `0x10014DC8`) is the last solid MCVar internal call edge, but the exact old boundary is now narrowed: `0x10014CBE` is a `CRequestID` lifecycle/propagation helper, not a constructor and not proven `StartRequest`. It loads a linked object from `[this+4]`, copies `[this]` to linked-object `+0x24`, and calls linked-object vtable slot `+8`.

The named MCVar request interface is `CRequestID`: constructor `0x1000E044` is typed `CRequestID(CVar2*, IUnknown*, IDispatch*, unsigned long)`, while `MakeCB` `0x100148B8` is typed with `CDdeAction**` and six VARIANTs. `MakeCB` also reaches `CXVariant::Set` on an `NCDDE_BINARY_HEADER`-typed path and dispatches through object slots `+0x14`, `+0x18`, and `+0x1c`. This is strong intra-MCVar request/DDE semantic evidence, but it does not prove that the linked object at `0x10014CBE` is the `CDdeAction` instance at the overlapping `StartRequest` label.

The prior `CDdeAction::StartRequest(CAtom&)` candidate around `0x10004AF6` remains unreliable because raw bytes indicate an overlapping/misaligned function boundary; the useful prologue is around `0x10004AC8`. Consequently:

- `ReadVar → StartRequest` is **not** a proven direct call.
- `ReadVar → 0x10014CBE` and `0x10014CBE`’s linked-object/vtable-slot `+8` operation are solid static edges.
- The request-region vcall around old `0x10004E1D` through `[esi]` vtable `+4` is a real indirect operation, but its object allocation, vtable address, and target remain unresolved.
- `CRequestID::MakeCB` to a concrete runtime `CDdeAction` instance remains dashed despite its recovered typed signature.

This remains the causal gap between MCVar’s Automation/request object graph and the ncdde transport. The graph now records the recovered CRequestID edges as solid and keeps the runtime object identity and cross-module transport edges dashed.

## 3. ncdde transport and recovered serializer

### Registration/callback side

Old ncdde registration is concrete:

```text
0x421041 DdeInitializeA(callback=0x401983, flags=0x001A9000)
0x401983 → 0x420AA0 → 0x402388 → 0x420B20
0x4211C7 DdeNameService(idInst=[object+0x2510], service=[object+0x2514], register=1)
```

`0x420B20` is a coherent callback dispatcher with verified transaction cases including `0x1030`, `0x1062`, `0x2022`, `0x4010`, `0x4090`, `0x8072`, and `0x80C2`. The `0x2022` case reaches `DdeCreateDataHandle` at **`0x420C4A`**, with arguments derived from object fields (`+0x2510`, `+0x2628`, `+0x262C`, `+0x2634`, `+0x2638`) and clears `[object+0x262C]` on success. This is a proven callback-side data-handle mechanism, not a proven `XTYP_REQUEST=0x20B0` response.

The real application request dispatcher is **`0x448AC0`**. At `0x449265`, `[ebp+0x0C]` is `wFmt`, with branches for `CF_TEXT=1`, registered binary format `[0x499950]`, and `CF_OEMTEXT=7`. Its special item path at `0x4492BD` calls the imported `DdeCreateDataHandle` thunk with `pSrc=0x479C64`, `cb=6`, and `wFmt=7`. The normal path starts at `0x4492D3` and enters object/producer helpers.

### Recovered normal serializer/object path

The following transport-side edges are solid at the static level:

```text
0x449301 → 0x401BD1 → 0x440940   record/object construction and copy
0x449301 → 0x402487 → 0x442960   output-slot / format transfer
0x449301 → 0x402842 → 0x442C80   object lookup/creation fallback
0x449301 → 0x4021AD → 0x44A440   request-state / per-item producer dispatch
0x44A440 → 0x40203B → 0x44A730   per-item serialization call
0x44A730 → type writes at 0x44AA37, 0x44AA42, 0x44AA4D
0x44A730 → sequence/global uses at 0x44AA8A and 0x44AAB4..0x44AAB7
0x44A730 → count/size fields at 0x44AABC and 0x44AACA
0x44A730 → 0x44AD50 → 0x44AE23 → DdeCreateDataHandle
```

The recovered serializer initializes the old `0x44A5AA` header region with `0x14` at `+0`, marker `0x44A5BA`-associated state, and `0xF6F7F8F9` at `+0x10`; it calls `0x40203B` from `0x44A60A` while iterating items. The current phase’s newer recovered targets identify the actual serializer at `0x44A730`, type stores at `0x44AA37/42/4D`, global sequence uses at `0x486884` via `0x44AA8A` / `0x44AAB4..0x44AAB7`, size/count writes at `0x44AABC/0x44AACA`, and final handle creation through `0x44AD50 → 0x44AE23`.

`0x466FF8` is the `DdeAddData` import thunk. Its presence confirms a data-handle append/update capability in ncdde, but the available xrefs do not establish that the MCVar ReadVar object reaches this thunk or that it participates in the recovered normal serializer path.

## 4. Old/new comparison and causal conclusion

| Stage | Old | New/equivalent | Status |
|---|---:|---:|---|
| ReadVar public virtual entry | `0x1000BC74` | `0x1000BD86` | solid identity/shape |
| SAFEARRAY copy/iteration | `0x1000C602`, OLEAUT32 calls | relocated equivalent reported, full body not recovered | old solid; new partial |
| request construction helper | `0x10014CBE` | `0x10014DC8` | solid direct helper identity |
| StartRequest candidate | around `0x10004AF6`, overlap warning | not recovered as a trustworthy entry | dashed semantic join |
| request-object vtable call | `[esi] + 4` around old `0x10004E1D` | equivalent target not recovered | solid indirect operation; target dashed |
| ncdde registration/dispatcher | `0x421041`, `0x420B20` | new relocation not independently enumerated here | solid old transport facts |
| normal serializer | `0x44A730` and listed callees | target-set provided by current recovery | solid static edges |
| MCVar object → ncdde object identity | not recovered | not recovered | dashed/unproven |
| serializer → captured `+0x07` changing byte | no proof; `0x420730` writes constant `2` | no proof | dashed/unresolved |

The recovered serializer’s sequence/global accesses are therefore **not** evidence that MCVar’s `ReadVar` owns or increments the captured `+0x07` byte. MCVar’s coherent header stores remain zero/literal `0x17`/`0x06` at `+6`, while ncdde’s known `0x420730` writer stores constant `2` at `+7`. The shared object, buffer, and byte-level data-flow edges remain unresolved.

## 5. Remaining high-value proof steps

1. Recover the actual new `ReadVar` body/xrefs and verify whether `0x10014DC8` reaches a concrete COM interface or request object.
2. Rebuild the overlapping old `StartRequest` and `GetNcddeBinaryData` boundaries from raw bytes, then identify the vtable object and slot target.
3. Backward-slice the buffer passed by `0x44AD50/0x44AE23` and test for a value originating in an MCVar SAFEARRAY/VARIANT.
4. Resolve the `0x20B0` request callsite to the normal serializer rather than treating the separate `0x2022` callback data-handle path as equivalent.
5. Locate any post-`0x420730` overwrite of `+7`; current evidence only proves a constant `2` store there.

## Sources

- `research/functions/old_readvar_flow.rz`
- `research/functions/architect_evidence_summary.md`
- `research/functions/new_request_response.rz`
- `research/logs_asmb/phase8_impl_44a440.objdump`
- `research/logs_asmb/phase8_header_writer_420730.objdump`
- `research/logs_asmb/66_rizin_datahandle_xrefs_raw.txt`
- `research/logs_asmb/68_consolidated_request_trace_raw.txt`
- `research/logs_asmb/79_objdump_dde_imports_raw.txt`
- `research/FINAL_REPORT.md`
