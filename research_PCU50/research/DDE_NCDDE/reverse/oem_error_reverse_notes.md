# NCDDE serializer/OEM/error verification (Phase 11)

## Verdict
**Verified with limitations.** The old `ncdde.exe` contains a bounded, statically recoverable serializer at VA `0x44A5A1` through its return paths, plus the forwarding/response path at `0x44A680`, `0x44AD50`, and `0x44AE23`. The exact byte stores and observable return values are verified below. The `0x85000903` origin is **not verified** and is localized only as an external/indirect runtime value: it is absent as a literal in the scanned old/new `ncdde.exe` and `MCVar.dll` images. `OEMTEXT` rejection is statically supported, but it is **not** proven to cause `0x85000903`.

## Inputs and method
- Old image: `/root/PL/PCU_old/H/mmc2/ncdde.exe`, PE32 x86, image base `0x400000`, 573,488 bytes.
- New image: `/root/PL/PCU_new/C/RECYCLER/S-1-5-21-4025392478-4199590385-3038547483-1005/Dc28/files/F/mmc2/ncdde.exe`, same size.
- MCVar images: old 434,769 bytes; new 439,177 bytes.
- No live/vendor execution was used. Originals were not modified. Disassembly was produced with GNU `objdump -D -Mintel --start-address=0x44a5a0 --stop-address=0x44ae51` against the old image. The raw output is `FUNCTIONS/ncdde_serializer_phase11.asm`.

## Exact serializer evidence
The entry region at `0x44A5A1` initializes and fills a global response buffer at `0x486BD0`:

- `0x44A5AA`: `66 c7 05 d0 6b 48 00 14 00` -> WORD `[0x486BD0] = 0x0014`.
- `0x44A5B3`: `66 89 15 d2 6b 48 00` -> WORD `[0x486BD2] = 1`.
- `0x44A5BA`: `c7 05 e0 6b 48 00 f9 f8 f7 f6` -> DWORD `[0x486BE0] = 0xF6F7F8F9` (a sentinel/default field, not claimed to be a wire value).
- `0x44A5C4`: `66 c7 05 d6 6b 48 00 00 00` -> WORD `[0x486BD6] = 0`.
- On the normal loop, `0x44A62D` checks a mode/flag at stack `[esp+0x2c]`; if it equals 1, `0x44A636` stores byte `0` at the current output pointer and increments that pointer. This is the only statically demonstrated NUL terminator in this bounded serializer path.
- At `0x44A650`, the object virtual call receives `0x486BD0` as its buffer argument. If the object is absent, the path at `0x44A66E` computes the produced length as `current_pointer - 0x486BD0` and forwards it to `0x4012F8`.
- `0x4012F8` is a thunk/jump to `0x44AD50` in the supplied focus evidence (`reviewer_track_b_focus.asm`, line 244). Thus the serializer's forwarding ABI is pointer/length based; no C prototype or calling convention beyond the observed x86 stack sequence is asserted.

The packed transition/counter bytes are exact:

- `0x44AA37`: WORD `[0x486BD4] = 1` (`01 00`); `0x44AA42`: WORD = 2 (`02 00`); `0x44AA4D`: WORD = `0x64` (`64 00`). These are selected through a bounded jump table for values 0..3; do not infer semantic labels for the selectors beyond the stores.
- If the mode byte at `[esp+0x3c]` is nonzero, `0x44AA5E` sets bit 0 at byte `[0x486BD5]`.
- `0x44AA8A` reads byte `[0x486884]` (global sequence/counter state).
- `0x44AA92` zero-extends byte `[esp+0x20]` into `CX`; `0x44AA98` copies the sequence byte into `DL`; `0x44AA9A` shifts it left 8; `0x44AA9D` adds `CX`.
- `0x44AAA3`: `66 89 15 d6 6b 48 00` -> WORD `[0x486BD6] = DX`. Therefore the packed WORD is exactly `(uint16_t(sequence_byte) << 8) | uint16_t(input_byte)` under the observed instructions, stored little-endian in memory.
- `0x44AAB4` increments `AL`; `0x44AAB7` writes the incremented value back to `[0x486884]`, after the read and after the packed store. This confirms read-before-store and increment-after-store ordering, but does not establish global uniqueness or external causality.
- `0x44AABC`: DWORD `[0x486BD8] = (end_pointer - start_pointer) + 1`.
- `0x44AACA`: DWORD `[0x486BDC] = output_pointer - object_pointer + selected_index` (as expressed by the exact instructions); this is not reinterpreted as a protocol field without a caller contract.
- For an error/negative element (`0x44AB71`), `0x44AB7A` sets WORD `[0x486BD4] = 0xFFFF`, copies an object error DWORD into `[0x486BD0 + low16(pointer)]`, adds 4 to the WORD at `[0x486BD0]`, increments WORD `[0x486BD2]`, zeros `[0x486BD8]` and `[0x486BDC]`, and advances the caller pointer by 4. The exact bytes are present; semantic field names remain deliberately conservative.

Return statuses observed in the bounded body:
- `0x44A659..0x44A662`: returns `0` after cleanup.
- `0x44A663..0x44A66D`: returns `-1`.
- `0x44ABBB..0x44ABC7`: returns `1`.
- `0x44ABC8..0x44ABD4`: returns `-2`.
- `0x44ABD5..0x44ABF4`: returns either `-3` or `-2` depending on `[object+7]`; this is a return convention observation, not an error decoder.

## Forwarding / OEMTEXT localization
The bounded path at `0x44AD50` selects an offset from the object based on the mode (`+0x8A` if mode 1, otherwise `+0x8E`), checks object state byte `+7`, and eventually reaches `0x44AE23`:

- `0x44AE00` derives a boolean from `ECX`, pushes the observed arguments, and calls `0x466F56` at `0x44AE23`.
- The return is written to `DWORD [EBX]` at `0x44AE2A`. Zero enters `0x44AE2E`, which calls `0x40239C` with literal `0x15` and returns zero; nonzero stores `EBP` to global `[0x485888]` at `0x44AE42`.
- This proves the forwarding and response-call locations, not the meaning of each opaque object parameter or the source of an application-level error code.

For the special OEM path, the existing focused receiver evidence shows:
- Receiver VA `0x448AC0` dispatches transaction type `0x20B0` to `0x449265`.
- Format value `7` is treated as `CF_OEMTEXT` in the ordinary processing branch, not as an item ordinal.
- The OEM path compares the requested handle with the current item via `DdeCmpStringHandles` at `0x449299` -> `0x466F26` -> IAT `0x6C631C`.
- Equality selects source VA `0x479C64`; the independent assertion artifact verifies the six bytes `4E 63 64 64 65 00` (`Ncdde\0`). A nonzero comparison branches to `0x449A53`; the epilogue returns zero. Thus the special response bytes are verified, while a particular client-visible interpretation is not.

## 0x85000903 hypothesis: rejection/localization
The focused literal scan artifact `FUNCTIONS/reviewer_track_b_error_literal_scan.json` reports no matches in all four exact old/new `ncdde.exe` and `MCVar.dll` files for:

- little-endian DWORD bytes `03 09 00 85`;
- big-endian bytes `85 00 09 03`;
- ASCII text `85000903`;
- UTF-16LE text `85000903`.

The existing executable-section immediate scan additionally found no candidate immediate for `0x85000903`, `0x85000900`, or `0x85000000` (recorded in `FUNCTIONS/reviewer_error_cleanup_audit.asm`). This is a bounded negative result only: it cannot exclude arithmetic construction, a table/lookup, a value returned by another DLL/device, or propagation through an unscanned module.

**Conclusion:** the observed runtime corpus can establish that `0x85000903` occurred in an MCVar slot, but static NCDDE bytes do not establish its origin or decoder. The OEMTEXT mismatch/rejection path is not evidence that it generated that code. Any claim that OEMTEXT causes `0x85000903`, or that NCDDE directly contains/decodes that constant, is rejected pending a client/runtime trace or a proven producer path.

## Files
- Created: `/root/PL/research/phase11/FUNCTIONS/ncdde_serializer_phase11.asm` (raw bounded objdump output, VA `0x44A5A0..0x44AE50`).
- Created: `/root/PL/research/phase11/FUNCTIONS/ncdde_error_oem_verification.md` (this report).
- No input binaries or prior evidence files were modified.
