# Stage 16.6 Correction C: actual function boundaries

## Scope and inputs

Offline static analysis only. Exact old and new `MCVar.dll` inputs were hashed before examination and matched the stage16.5 records. Both are PE32/i386 with image base `0x10000000`; old `.text` is VA `0x10001000` size `0x2af36`, new `.text` is VA `0x10001000` size `0x2b046`. No binaries were executed and no collector, DDE, Windows tooling, or source/archive modifications were used.

The prior [FUNCTION_MAP.json](/root/PL/stages/stage16_5/reports/FUNCTION_MAP.json) is preserved unchanged and explicitly treated as superseded evidence, not overwritten.

## Findings

- `ReadVarAsync` entries `0x1000d28a` (old) and `0x1000d39c` (new) are validated: both begin with the same 30 raw bytes, decode as x86 instructions, and contain direct calls into the transaction starter at old `0x1000d7a4` and new `0x1000d8b6`.
- Rizin's legacy `ReadVarAsync` labels at old `0x1000d3f6` and new `0x1000d508` are rejected as independent entries. The preceding block falls through, and the label occurs in the instruction stream after `mov eax,[eax+0x0c]` / `mov eax,[eax]`. No independent prologue, predecessor, or standalone function boundary validates the alleged 18-byte function.
- Do not treat the reported 690-byte size as a proven contiguous function extent. Shared/tail control flow around old `0x1000d4f8/0x1000d53c` and new `0x1000d60a/0x1000d64e` prevents a unique boundary assignment from these bytes alone.
- The decorated DataChange names at old `0x10012b4c` and new `0x10012c5e` are not reliable actual entries: each begins implausible bytes and reaches a `ret 4` before a structured prologue at old `0x10012b78` / new `0x10012c82`. That following region begins with `CTransactionID::CloseUp` diagnostics. Do not assign the later prologue to DataChange solely by proximity.
- IdleCB labels old `0x10012c01` and new `0x10012d13` overlap the large structured region and begin invalid/misaligned bytes. No standalone prologue or direct-call target independently validates them.
- FlushCyclics labels old `0x10012d7f` and new `0x10012e91` also begin invalid/misaligned bytes within the region. Previously observed block behavior, including the new conditional direct call `0x100134ab -> 0x100139c2`, remains block-level evidence only. It does not validate the named function start.
- Therefore the complete `DataChange -> pending -> IdleCB -> FlushCyclics` chain remains unresolved. No corrected standalone code VA is asserted for these cyclic labels.

## Method and artifacts

Used `sha256sum`, `file`, GNU `objdump -h/-d`, Rizin `aaa; afl` and `pd`, and Capstone 5.0.7 x86-32 decoding. Raw objdump captures cover the async and transaction-starter regions. `capstone_boundary_scan.txt` records the entry and cyclic-label decode checks. Rizin and objdump show the entry labels/overlapping boundaries; Capstone independently verifies instruction decoding and the terminal `ret 4` sequences. These are static boundary claims only, not dynamic behavioral claims.

See [corrected_function_map.json](/root/PL/stages/stage16_6/corrections/boundaries/corrected_function_map.json) for entries, confidence, binary identity, and exact warnings. The earlier [corrected_function_boundaries.json](/root/PL/stages/stage16_6/corrections/boundaries/corrected_function_boundaries.json) remains in the directory as prior generated content and was not used as the authoritative result.
