# Stage 15: MCVar Async/Cyclic and Collector Foundation

## Verified progress

- Workspace/source discovery completed. `PCU_old`, `PCU_new`, and `research` remain unchanged; new work is under this directory.
- Both preserved MCVar builds are PE32/i386 at image base `0x10000000`, with source paths, hashes, resource inventory, Rizin capability/string inventories under `evidence/` and `reverse/`.
- Both DLLs contain an embedded 19,732-byte MSFT TypeLib (`TYPELIB/1/1033`). The historical extraction and hashes are preserved; complete exact TypeInfo decoding remains in progress.
- Native diagnostic package now cross-builds reproducibly as PE32/i386 with strict warnings enabled. Two consecutive builds produced identical bytes; artifact: `diagnostics/stage15_diag.exe`, SHA-256 `74017de1c6538fc10787e784510145ccadc4e98167468ee5c0f00184f243652a`.
- Review defects were corrected: Windows batch launcher conditional grouping, deterministic build timestamp, stale artifact hash, and cross-mapped `ItemResult` acceptance. The mismatched-result guard has a regression test.
- Prior real-PCU synchronous baseline remains the supported fallback: 1..20 variable batches were observed; item-level errors and quality matter independently of outer HRESULT.

## Acceptance status

| Criterion | Status |
|---|---|
| Preserve prior source evidence | PASS; no source tree writes performed |
| Establish both binary identities | PASS |
| Exact old/new TypeLib ABI | OPEN; raw TypeLib present, decoding not yet complete |
| Runtime async/cyclic behavior | OPEN; no Windows/PCU runtime here |
| Collector offline foundation | IN PROGRESS in `collector/` |
| Native diagnostic package | IN PROGRESS in `diagnostics/` |
| Независимый повторный reviewer | CONDITIONAL PASS: 9 tests, reproducible PE32 build/hash and CMD guards verified; ABI/runtime remain open |
| Physical PCU claims | NONE made |

## Safety

No physical PCU was available or contacted. No MCVar write, PLC/NC control method, DDE action or machine-parameter mutation was performed. Unverified async/cyclic methods are not called.
