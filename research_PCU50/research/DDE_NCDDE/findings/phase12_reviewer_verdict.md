# Phase 12 Independent Reviewer Verdict

Date: 2026-10-31
Scope: offline, read-only final review of Phase 12 Tracks A/B/C/D, with independent raw `objdump` and Rizin checks and rerun tests. No vendor executable was run; no live PCU or industrial equipment was contacted; no binary or investigator artifact was modified.

## Verdict

**VERIFIED WITH LIMITATIONS.** The offline evidence package and its bounded collector/parser contracts are reproducible. The stronger causal, batching, live-runtime, and full old/new semantic-equivalence claims are **not verified**. The package must not be represented as proving a continuous MCVar COM -> NCDDE chain.

## Evidence basis

Critical image hashes were independently collected for old/new MCVar.dll and old/new ncdde.exe; all are PE32 i386 and differ by image/build. Raw focused windows are preserved in `REVIEWER_RAW_EVIDENCE/02_critical_disassembly.txt`.

Independent byte facts:

- Old MCVar `0x1000BD47 -> 0x1000C532`; new MCVar `0x1000BE59 -> 0x1000C644`. Both continue through analogous local result/error handling. Neither raw window contains a direct USER32 message call or NCDDE cross-module join.
- Old NCDDE reads `[0x486884]` at `0x44AA8A`, stores packed WORD `[0x486BD6]` at `0x44AAA3`, increments AL at `0x44AAB4`, and writes `[0x486884]` at `0x44AAB7`. This is local guarded writer evidence, not MCVar causality.
- New NCDDE at `0x4485F7` is a distinct format-7/OEM path using new globals and `Ncdde\0` at `0x479068`; searches found no old counter-address operands. Address coincidence is rejected as equivalence.
- Old MCVar imports include `PostMessageA` and `SendMessageA`; import presence is not a ReadVar invocation trace.

## Tests and execution evidence

- Phase 12 parser and collector tests: **11/11 passed** via unittest.
- Phase 11 runtime/corpus unittest suite: **7/7 passed** from its documented script directory.
- Standalone Phase 11 corpus script: **5/5 passed**.
- Old NCDDE byte verifier: **9/9 byte assertions passed**.
- `pytest` was unavailable (`No module named pytest`); equivalent unittest suites passed. An initial wrong-directory combined unittest invocation had one import error; documented-directory rerun passed all 7 tests.

## Eight user gates

| Gate | Status | Independent basis |
|---|---|---|
| 1. Critical MCVar request boundary/addresses | **ACCEPT** | Raw bytes independently confirm old `0x1000BD47 -> 0x1000C532` and new `0x1000BE59 -> 0x1000C644` with analogous local handling. ACCEPT is limited to the boundary, not transport. |
| 2. Concrete MCVar transport/message/API bridge | **FAIL** | Imports and subsystem strings exist, but no checked ReadVar-to-PostMessage/SendMessage edge, HWND/topic/format/transaction argument flow, or NCDDE join. |
| 3. MCVar response ownership / VARIANT mapping | **PARTIAL** | Callback/result-shaped local operations exist, but concrete vptr installation, slot target, ownership, and DDE_DATA-to-VARIANT chain are absent. |
| 4. Old NCDDE counter and serializer facts | **ACCEPT** | Old critical writer bytes and verifier pass; serializer/header facts are bounded to the old image and guarded path. |
| 5. New NCDDE counter/old-new equivalence | **FAIL** | Old address references are absent in new image; distinct new OEM path is verified, but no semantic counter equivalent or normalized equivalence proof exists. |
| 6. Aggregate HRESULT/error/quality/cache/timestamp semantics | **FAIL** | Replay observations are real/useful, but exact aggregate CFG and producer/provenance branches remain open. |
| 7. Offline tests and bounded collector contract | **ACCEPT** | All discovered relevant unittest suites pass; parser rejects malformed captures; collector tests preserve order/duplicates and separate outer/item status. |
| 8. Final causal/batching/architecture claim | **PARTIAL** | Conservative read-only adapter recommendation is supported. Continuous MCVar-to-NCDDE causality, one-item/one-increment batching, freshness, atomicity, and full compatibility are not established. |

## Questions 1-15

The Phase 12 material exposes H01-H20 rather than a separately numbered Q1-Q15 list. For the requested fifteen-question review, the applicable question dispositions are:

| Q | Disposition | Finding |
|---|---|---|
| 1 | **ACCEPT** | Old/new MCVar request-preparation boundaries are byte-verified. |
| 2 | **FAIL** | A concrete ReadVar -> WM_DDE_REQUEST/API edge is not proven. |
| 3 | **PARTIAL** | SAFEARRAY/VARIANT preparation and order are supported; submission granularity is not. |
| 4 | **FAIL** | MCVar-to-NCDDE process/window/conversation identity join is absent. |
| 5 | **PARTIAL** | Callback/result-shaped indirect calls are present; ownership/vtable target is unresolved. |
| 6 | **ACCEPT** | Old counter read/pack/increment/write bytes are independently verified. |
| 7 | **FAIL** | New-image semantic counter equivalence is not established. |
| 8 | **PARTIAL** | Old serializer/header and guarded ABI facts are verified; complete type/count dictionary is not. |
| 9 | **FAIL** | Count >1 wire semantics are not established by scalar captures/static evidence. |
| 10 | **FAIL** | CF_TEXT/binary shared backend/cache equivalence is not established. |
| 11 | **PARTIAL** | OEM format-7 equality path is visible; registration/lifetime and failure attribution remain open. |
| 12 | **FAIL** | Aggregate HRESULT decision procedure is not recovered. |
| 13 | **FAIL** | Error namespace/provenance is not recovered; literal observations are insufficient. |
| 14 | **FAIL** | Quality `0x00C0` origin is not recovered. |
| 15 | **PARTIAL** | A bounded read-only collector contract is defensible, but freshness/atomicity and causal transport remain unknown. |

## Track dispositions

- Track A: **PARTIAL**. Request preparation and local result handling are proven; concrete message bridge and response ownership are not.
- Track B: **PARTIAL**. Old writer/serializer facts are proven; new counter equivalence, complete semantics, and handle origin are not.
- Track C: **PARTIAL**. Offline behavior is reproducible; aggregate/error/quality/cache/timestamp causality is not.
- Track D: **PARTIAL**. Conservative adapter architecture is justified; direct protocol implementation and full compatibility are not.

## Claims explicitly rejected

- `197/197` replay transitions as proof that every MCVar item caused one NCDDE increment.
- USER32 import presence as proof of the checked ReadVar branch's message call.
- Old NCDDE `0x486884` or `0x44AA8A` as new-image equivalents.
- `0x10004E2E` or cleanup calls `0x10014CBE`/`0x10014DC8` as proven transport submission.
- `0x85000903` as proven CF_OEMTEXT rejection provenance.
- Any freshness, atomicity, server identity, or single-snapshot claim based only on replay labels.

## Required evidence for a stronger verdict

A stronger causal verdict requires a bounded read-only trace joining one ReadVar entry/return to message/API arguments or alternate transport, process/window/conversation identity, NCDDE transaction, counter write, response decode, output stores, and aggregate return. Full old/new acceptance additionally requires normalized CFG/data-flow comparison of MCVar and NCDDE serializer/error/cache/vtable paths.
