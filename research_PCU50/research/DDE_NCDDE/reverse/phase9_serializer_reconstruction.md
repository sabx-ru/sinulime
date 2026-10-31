# Binary serializer reconstruction (offline)

## Scope and evidence

Target: `PCU_old/H/mmc2/ncdde.exe` (PE i386), static disassembly only. Raw local disassembly: `logs_asmb/phase9_serializer_44a730_44ad50_raw.asm`; relevant ranges 0x44A730-0x44ABF4 and 0x44AD50-0x44AFBD. No vendor runtime, live DDE, network, SHA, or modification of binaries/captures was used. Capture corpus is `../real_tests/logs/02_RUN_RESEARCH/*binary.bin` (328 files). The phase-9 brief's 166 chronology pertains to a subset/earlier collection; regression enumerates current binary captures and reports its actual count.

## Producer: 0x44A730

This is a generic value-to-stream serializer, not a fixed structure copy. It receives a value descriptor selected by index from a collection (`[root+0xA6][index]`) and a parallel descriptor from another indexed collection. It obtains provider/object state through vtable-backed calls. Descriptor fields include offsets +0x02/+0x06 and +0x12; `0xFFFFFFFF` is a sentinel and ranges are computed inclusive (`end-start+1`). A second bounds/range is derived from provider fields. Exact source-level class names are unavailable, so do not equate these internal descriptors with public C++/COM types.

The `+0x2A` byte (or provider byte `object+0x3E` when it is `0xFF`) selects a conversion/stringification behavior. A separate descriptor value at +2 or provider flag `(object+0x20 >> 5)&1` influences the starting element/index. Main loop writes to caller's output cursor. It may emit delimiter `0x7C` in a specific flag/type case. For element serialization it calls the provider object's virtual method at vtable +0x1C, passing descriptor metadata, element position, output cursor, and out-length/result slots. Return codes `-3` and `-2` propagate as special failures; `-1` triggers a fallback virtual call at vtable +0x18. Results are segmented at 0x1388 (5000) bytes; the method tracks continuation position and may grow/rebase output through 0x4012F8. A 0x200 limit is consulted on a non-text path. This routine does not itself prove a uniform element width: width is determined by provider/type conversion, and strings use variable-length output. The capture packet's length field is not sufficient to infer a native array element size.

## Wrapper/flush: 0x44AD50 and 0x44AE23

0x44AD50 chooses a destination subobject by the input discriminator (`base+0x8A` when discriminator=1, otherwise `base+0x8E`). For the binary header condition (`base[7]==2`) plus provider/state conditions, it selects the specialized aggregation branch. If the accumulator pointer is null, 0x44AE23 calls internal helper 0x466F56 with seven arguments; stack pushes resolve as state at 0x4A6CC0, data pointer, byte length, zero offset, item handle 0x486864, format/discriminator, and a boolean flag. This helper is an internal DDE-data append/create adapter; import thunk inventory identifies `DdeAddData` in this module, but without the thunk body/argument provenance here, do not assert 0x466F56 is a direct imported `DdeAddData` call. The other branch calls 0x466FF8 to append/construct using an existing handle. Subsequent code updates global byte counts and can append string chunks. The captured packet evidence indicates a 20-byte common header followed by padded payload; observed header fields include little-endian 0x14, 1, 0x64, marker bytes F9 F8 F7 F6 at +0x10, one changing byte +7, and a data length at +0x0C. Capture analysis labels count candidate=1 and `length-20` as element-size candidate; these are empirical labels, not a type/count/stride contract proven by this function.

## Type, count, element size, ordering

- Value class: provider-backed typed value descriptor; exact class/type enum mapping unresolved. Descriptor byte +0x2A and provider metadata govern conversion. The string-like path and numeric/typed path are visibly distinct.
- Count: serializer iterates an inclusive descriptor range and/or provider-reported range, with start/continuation state. Captured sample packet header candidate count is 1. That is not evidence every source value is scalar.
- Element size: no global fixed size. Typed virtual conversion writes its own output; string conversions are variable length. Captures' payload-size candidate (total bytes minus 20) describes packet payload region, not necessarily a source element stride.
- Sequence writes: per-item output cursor advances as conversion emits bytes; chunking boundary is 5000 (`0x1388`). Accumulator appends segments and tracks total length; optional separators are `|` (0x7C). The wrapper's format-specific path creates/appends data handle and records accumulated length. No proof that captured +7 sequence byte is written in these functions; +7 is checked for value 2, while a distinct byte at +0x84 increments during a specialized path. Keep the sequence-byte source unresolved.

## Capture regression

Run from any directory: `python3 research/tools/phase9_binary_serializer_regression.py`. It is offline and read-only. It parses every `*binary.bin` in the existing research capture folder, validates minimum header size, header-size field, marker, stored payload-length consistency, and groups common header/length distributions. It does not claim runtime parity or infer native element stride.

## Limits

The exact vtable concrete implementation, internal value enum names, and ownership/meaning of header +7 remain unproven. The artifact is a bounded reconstruction rather than a fully executable encoder model: captures do not expose the original source values for all requests, and the serializer relies on proprietary provider virtual methods. The regression script tests reproducible packet invariants, not byte-for-byte regeneration from source values.
