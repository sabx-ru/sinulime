# PowerLine target/xref and buffer-field evidence

Scope: offline static analysis only, old/new `ncdde.exe` plus old `MCVar.dll`; no vendor execution or live IPC. The raw command output is [focused_xrefs_fields_raw_20261031.txt](/root/PL/research/logs_asmb/focused_xrefs_fields_raw_20261031.txt).

## Binary identity

- Old `PCU_old/H/mmc2/ncdde.exe`: SHA-256 `40a030e0a7364aa358ae36494be1304810855997fb81804db91ea6fc05223916`.
- New `PCU_new/.../mmc2/ncdde.exe`: SHA-256 `a3f507c8f351aac617c8342abb1e0fb2aeee980d20301c4659d6bf472110ba7c`.
- Old `PCU_old/H/mmc2/MCVar.dll`: SHA-256 `43a5c1991d98b6b6e155233a0114d7ff72bf4dec7edf58d0607da501e7d98712`.

## Direct target xrefs

### Old ncdde.exe

Import/bridge thunks:

- `0x401A87 -> 0x43D0C0`.
- `0x402167 -> 0x43B830`.
- `0x401EC9 -> 0x43D290`.
- `0x402018 -> 0x43CF50` (the 0x43CF50 request-wrapper entry).

Direct calls recovered by objdump and independently confirmed with Rizin `axt`:

- `0x43CF90 -> call 0x402167`.
- `0x43CFD6 -> call 0x401A87`.
- `0x43D013 -> call 0x401EC9`.
- `0x43D24A -> call 0x401A87`.

Rizin also reports `0x402018 -> jmp 0x43CF50`; no other old direct caller of `0x43CF50` was recovered by the target-xref scan. `0x43CF50` therefore acts as the principal old wrapper entry through the `0x402018` thunk.

### New ncdde.exe

- `0x40142E -> jmp 0x43CF50`.
- `0x43F3F3 -> call 0x401EC9`.
- `0x4432F5 -> call 0x401A87`.
- `0x44433C -> call 0x401A87`.
- `0x4473F4 -> call 0x401A87`.
- `0x447554 -> call 0x401A87`.

The new image has materially different wrapper layout/callers; do not transfer old `0x43CF90/0x43CFD6/0x43D013` caller semantics into the new image. Rizin independently confirms the four `0x401A87` callers and the `0x43F3F3` `0x401EC9` caller.

## Old 0x43CF50 data-flow and helper fields

The raw disassembly at `0x43CF50` shows a `this`-like object in `ESI` and a 12-byte stack-cleanup convention (`ret 0xc`):

- `0x43CF75`: load `[ESI+0x0D]`; nonzero value is passed to `0x4019E2`, then `[ESI+0x0D] = 0` at `0x43CF85`.
- `0x43CF8F/90`: pass the second argument to `0x402167`; returned `EAX` is stored into `[ESI+0x0D]` at `0x43CF9A`. A zero return takes the error/initialization branch.
- `0x43CFC8-D3`: load argument `[EBP+0x10]`, current `[ESI+0x0D]`, and `[EBP+0x08]`; push them in that order.
- `0x43CFD6`: call `0x401A87` with `ECX=ESI`. Return is compared to `1` at `0x43CFDB`; failure jumps to `0x43D056`.
- Success path allocates a 20-byte local context (`push 0x14`, allocator call `0x4663E4`), stores pointer in `[EBP+0x0C]`, then at `0x43D006-13` passes `ESI`, `[EBP+0x08]`, `[ESI+0x0D]`, and `[EBP+0x10]` to `0x401EC9`.
- `0x401EC9` is only a jump thunk; implementation is `0x43D290`. Its constructor-like code writes `[ESI+0x04]`, `[ESI+0x0C]`, and `[ESI+0x10]`, installs a vtable at `[ESI]`, and calls an object/IPC helper through `0x466426`.
- `0x401A87` is only a jump thunk; implementation is `0x43D0C0`. It computes a byte length from the buffer at stack/argument position `[ESP+0x0C]`, then passes the buffer pointer, computed length, format/state arguments, `[ESI+0x04]`, `[ESI+0x09]`, `[ESI+0x0D]`, and a local output pointer to `0x4025BD`. This is buffer/transaction handling evidence, not proof of a serialized MCVar header.
- `0x402167` is only a jump thunk; implementation is `0x43B830`. The shown entry builds a bounded local text buffer, copies a source string with `rep movsd/movsb`, and calls `0x466F0E`; this supports helper/error or IPC-string handling, not a proven packet producer.

## DDE / IPC API edges

Rizin resolves these old-image import thunks:

- `0x466F56 -> USER32!DdeCreateDataHandle`.
- `0x466F02 -> USER32!DdeClientTransaction`.
- `0x466F20 -> USER32!DdeGetData`.

Existing static xref evidence in `logs_asmb/66_rizin_datahandle_xrefs_raw.txt` gives old `DdeCreateDataHandle` callers at `0x4117A6`, `0x420C4A`, `0x4492BD`, and `0x44AE23`. These are separate callsites from the `0x43CF50` wrapper; no direct `0x43CF50 -> DdeCreateDataHandle` edge is proven. The request/response bridge and callback path must remain separate.

The old response-side region at `0x43D7B0+` calls `0x466F20` (`DdeGetData`) with a 0xDC byte count at `0x43D800`; it consumes a DDE data handle into a local buffer and then dispatches through object state. The direct presence of `DdeGetData` does not prove `XTYP_REQUEST` callback ownership.

## +6 / +7 / +10 and marker findings

### MCVar.dll: concrete header/state writes

Old `MCVar.dll` objdump gives the strongest field evidence:

- `0x10003E10`: `mov WORD PTR [EBX+0x6],DI`, immediately after `xor edi,edi` in the same construction region.
- `0x10003E14`: `mov DWORD PTR [EBX+0x10],0xF6F7F8F9`.
- `0x10004630`: `mov WORD PTR [EBX+0x6],0x17`.
- `0x1000470E`: `mov WORD PTR [EBX+0x6],0x06`.
- `0x1000445F/64`: load `[EBX+0x6]` and compare against another object field `[ESI+0x6]`.
- `0x100191D0`: `mov WORD PTR [ESI+0x6],AX` in a separate CRT-like/division routine; object identity is not proven.

Thus +6 is a 16-bit format/state field in the proven MCVar construction paths, with values 0, 0x17, or 6. The evidence does not support a monotonic counter interpretation. The marker constant is stored in little-endian instruction immediates as `F9 F8 F7 F6` (numeric `0xF6F7F8F9`), and is used at +0x10 in MCVar construction/validation paths. No direct ncdde writer of this MCVar header marker was proven.

### ncdde.exe field scan

The old ncdde scan shows many generic object accesses to +6/+7/+10. Relevant examples include:

- +6 consumers: `0x40A5DD`, `0x40A7AB`, `0x40AE16`, `0x40B644`, `0x411CC7`, `0x412254`, `0x4149BA`, `0x4466BF`, `0x4475FC`, `0x44886C`, `0x44A50D`.
- +7 copy/consume patterns: `0x408484-0x40849C`, `0x411D22-0x411D2C`, `0x411F34-0x411F3B`, and numerous state tests against 1/2.
- +6 writes in generic object/state code: `0x408498` byte-zero, `0x412E94` byte from `BL`, `0x417ED3` byte from `BL`, `0x41FE14` byte from `AL`, `0x428C31`, `0x42D054`, `0x42D10A`, `0x42D532`, `0x42D62B`, `0x4409D4`, `0x440A96`, `0x4414F8`, `0x448958`, and `0x456C28/0x458758/0x458A97`.
- +10 reads/writes are pervasive object/status accesses. The marker appears in ncdde as validation/reference use, including `0x4619E4: cmp [EAX+0x10],0xF6F7F8F9`, but this is not a proven header construction edge.

The generic ncdde +6/+7/+10 hits cannot be assigned to the MCVar header without a proven object identity. The safe conclusion is: ncdde consumes and transforms multiple helper/object fields; MCVar contains the concrete marker/header writes.

## Evidence boundary

Established: target thunk topology, all recovered direct callers in old/new images, old wrapper argument/field flow, old DDE import edges, concrete MCVar +6/+0x10 writes, and marker use.

Unresolved: a direct `0x43CF50` to `DdeCreateDataHandle` edge, a proven `XTYP_REQUEST` callback dispatch return path, and a cross-binary proof that any particular ncdde +6/+7/+10 object is the MCVar header. No live execution or IPC was used.
