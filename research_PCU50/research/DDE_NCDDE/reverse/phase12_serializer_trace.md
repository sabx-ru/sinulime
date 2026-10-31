# Track B NCDDE Serializer Follow-up

## Scope and evidence

Static-only analysis of:

- Old image: `PCU_old/H/mmc2/ncdde.exe`, PE32 image base `0x00400000`, timestamp 2004-11-02.
- New image: `PCU_new/C/RECYCLER/S-1-5-21-4025392478-4199590385-3038547483-1005/Dc28/files/F/mmc2/ncdde.exe`, PE32 image base `0x00400000`, timestamp 2011-07-25.

Commands and complete focused outputs are under `RAW_EVIDENCE/`. GNU `objdump` and Rizin were used independently. Neither image was executed and no capture was modified.

## Old callsite map

| Old VA | Static role | Inputs / guards | Output or next step |
|---|---|---|---|
| `0x448AC0` | request dispatcher | transaction in `[EBP+8]`; range/switch checks; global gate `[0x4A6D16]`; format and item branches | routes to producer, special OEM response, reject/cleanup |
| `0x44A440` | producer thunk/body | mode byte `[EBP+7] == 2`; compares request fields against globals `[0x486864]`, `[0x486868]`, `[0x48685C]`; fallback `0x4022A7` and object `+0x80` test | selects producer state; later initialization/iteration path |
| `0x44A730` | indexed element worker | object/table pointers from arguments; index `[ESP+0x10]`; metadata sentinel checks (`-1`, `0xFF`) and type bits | computes element state and data-dependent output width; errors can terminate path |
| `0x44AD50` | DDE output wrapper | chooses output pointer `arg+0x8A` for mode 1 else `arg+0x8E`; mode/type and object flags derive `ecx` boolean | existing-handle add path, new-handle create path, or error |
| `0x44ADDE` | add-data API call | only when output handle `*arg_8 == 0`, derived boolean nonzero, and `*selected_output != 0` | calls imported/user32 DDE add routine with `hData=*selected_output`, `pSrc=arg_ch`, `cb=arg_10`, `off=0`; stores result |
| `0x44AE23` | create-data API call | add path not taken, or selected output absent; uses instance `[0x4A6CC0]`, item `[0x486864]`, format `edi`, source `arg_ch`, length `arg_10`, boolean flag | creates new DDE data handle; stores result |
| `0x44AE5C` | add-data continuation | existing `*arg_8 != 0`; uses global accumulator `[0x485888]` as final argument, source/length and current handle | adds data, then accumulates `arg_10` into `[0x485888]` on success |
| `0x4492BD` | request/producer subpath near dispatcher | format/request state from dispatcher locals; enters normal producer/serialization branch after format checks | joins the guarded producer path, not an unconditional serializer entry |

The addresses above are old-image VAs only. They are not used as new-image identities.

## Bounded binary serializer

The old initialization at `0x44A5A1` establishes a bounded header region beginning at `0x486BD0`:

| Offset | Width | Static operation / interpretation | Confidence |
|---:|---:|---|---|
| `+0x00` | WORD | initialized to `0x14` (20); observed header size | confirmed |
| `+0x02` | WORD | initialized to version `1` | confirmed |
| `+0x04` | DWORD | computed length/offset state is written in serializer path | confirmed write, semantic name open |
| `+0x06` | WORD | packed value assembled at `0x44AA8A..0x44AAA3` | confirmed |
| `+0x08` | DWORD | computed serializer state/length write | confirmed write, semantic name open |
| `+0x0C` | DWORD | serializer state/length write path | confirmed write, semantic name open |
| `+0x10` | DWORD | marker `0xF6F7F8F9` | confirmed |
| `+0x14..+0x1F` | 12 bytes | reserved/initialization area; no universal field semantics proven | bounded but open |
| `+0x20` | variable | payload/cursor base for mode 3; otherwise the header base is used differently | path-dependent |

The preserved capture parser independently accepts only records with a 20-byte header, version 1, marker bytes `F9 F8 F7 F6` at offsets 16..19, and a declared payload length at offset 12. It observes 4-byte, 8-byte, and variable payloads. This is capture-format evidence, not proof that every old static path emits every captured record.

The serializer is bounded by a declared payload length and data-dependent cursor increments. The worker at `0x44A730` resolves each element through indexed object/type metadata and callback results; it is not a fixed-stride memcpy loop. Error/sentinel branches include metadata `-1`, `0xFF`, callback failure and exits around `0x44AB67`, `0x44ABC8`, and `0x44ABD5`. Thus a complete implementation must stop on the declared length and reject truncation/overrun rather than assume a universal element size.

The mode-3 path starts its cursor at `0x486BE4`; other modes use the initialized base `0x486BD0`. The count comes from the producer stack argument at `[ESP+0x18]`, and the worker loop increments its index and compares it to that count. Format/mode 1 has an explicit NUL/advance behavior. Flush/forwarding uses thunk `0x4012F8`; forwarding is separate from the counter increment.

## Old direct references

The exact objdump inventory is in `RAW_EVIDENCE/old_direct_refs_486884_486bd0.txt`.

- `0x486884`: exactly two direct instruction references: byte read `0x44AA8A` and byte write `0x44AAB7`. The read-modify-write is `mov al,[0x486884]`, packing/using `AL`, `inc al`, then `mov [0x486884],al`. It wraps modulo 256 and is not protected by a locally visible lock or atomic instruction.
- `0x486BD0`: 11 direct instruction references: header initialization (`0x44A5AA`), base loads/pushes/subtractions (`0x44A5DB`, `0x44A650`, `0x44A66E`, `0x44A675`, `0x44AB03`, `0x44AB24`), pointer/state stores (`0x44AB39`, `0x44AB71`, `0x44AB8B`), and cursor increment (`0x44AB95`). These are not all header-field accesses; some are block cursor/allocation/flush state.

The counter-derived packed WORD is `(old_counter << 8) | byte_at_[ESP+0x20]`, based on the byte load and subsequent stores around `0x44AA8A..0x44AAB7`. Its path is guarded by dispatcher, producer, worker, metadata, and callback conditions; it is not a per-request unconditional sequence.

## OEM/text versus binary

The format-7/item-equality branch in the old dispatcher uses the global item handle `[0x486864]`, compares against configured/global state, and creates the six-byte OEM source literal `Ncdde\0` at old literal VA `0x479C64`. This is a direct text-style response path and is separate from the typed binary serializer. Preserved captures show CF_TEXT as short NUL-terminated strings, while binary captures have the 20-byte header and typed payload.

## New-image comparison without address reuse

The new image has no direct instruction operands for old `0x486884` or old `0x486BD0` (empty `RAW_EVIDENCE/new_direct_refs_old_addresses.txt`). Therefore no old counter or old header identity is claimed for the new build.

Coherent new-image candidates are distinct:

- New format-7 path: `0x4485F7`, item handle `[0x48628C]`, comparator/config handle `[0x4A6740]`, instance `[0x4A66E8]`, source literal `Ncdde\0` at `0x479068`, DDE create call around `0x44862D`.
- New object-buffer path: `0x44D4CC..0x44D506` writes marker at buffer `+0x1C`, type at `+0`, size `0x20` at `+2`, and derived length at `+4`; it then locks/validates the buffer. A separate path at `0x44D5FF..0x44D64F` copies signed WORD length from object `+0x12` to buffer `+0x20`, writes marker, size `0x20`, payload length at `+4`, and length-minus-one at `+8`.
- The new `0x44A440` function builds a temporary object-pointer list and invokes virtual callbacks; its local count is not evidence of the old counter.

These candidates are structurally coherent but are not asserted to be ABI-equivalent to the old serializer without dynamic attribution.

## Evidence status

Confirmed: old direct xrefs, old guards, old argument pushes, bounded header writes, and distinct new-image candidate instructions. Open: semantic names for several header words, ultimate HSZ registration/initialization, runtime frequency, thread interleaving, and causal attribution of preserved captures to a particular branch.
