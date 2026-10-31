# Phase 11 Findings

## Verified new discoveries

1. **MCVar transport boundary is narrowed, not completed.** Fresh old/new MCVar inspection confirms the smallest actionable ReadVar edge is old `0x1000BD47 -> 0x1000C532` (RVA `0xBD47 -> 0xC532`) and relocated/new `0x1000BE59 -> 0x1000C644`. The callee performs substantive request/error and VARIANT preparation. No direct `PostMessageA`, `SendMessageA`, DDE transaction, target HWND, or NCDDE item mapping was recovered from this boundary.

2. **MCVar is a classic USER32 DDE component at subsystem level.** Imports include `PostMessageA`, `SendMessageA`, `PackDDElParam`, `UnpackDDElParam`, `ReuseDDElParam`, and `FreeDDElParam`; strings include `WM_DDE_REQUEST`, `WM_DDE_DATA`, `WM_DDE_ACK`, `ncdde`, and `ncddeBinary`. MCVar has no DDEML client imports in the inspected image. This supports the architecture hypothesis, not this ReadVar invocation's causal path.

3. **The previously suspected MCVar vtable transport edge is falsified.** At `0x10004E2E`, the reviewed vtable `0x1002C3A0` resolves slot `+4` to `0x100010D6`, whose bytes are `C2 04 00` (`ret 4`). This is a local result operation, not transport. Symbol labels around `StartRequest`/`StartPoke` overlap unreliable boundaries and are not accepted as direct edges.

4. **NCDDE request/response and counter path survive independent verification.** Rizin and GNU `objdump` agree on `0x448AC0` transaction dispatch (`0x20B0 -> 0x449265`), format-7 comparison, producer `0x4493D4 -> 0x44A440`, serializer `0x44A5A1/0x44A730`, packed state writer `0x44AA8A..0x44AAB7`, forwarding `0x44AD50`, and `DdeCreateDataHandle` at `0x44AE23` through the USER32 IAT.

5. **Counter writer semantics are precise locally.** The writer reads byte `[0x486884]`, packs `(old_byte << 8) | [ESP+0x20]` into WORD `[0x486BD6]`, then increments the global byte modulo 256. The writer is guarded and has distinct failure branches; this does not prove that all captured responses use it.

6. **CF_OEMTEXT path is resolved with an important limit.** Format `7` compares item handles; equality reaches `DdeCreateDataHandle` with six bytes `4E 63 64 64 65 00` (`Ncdde\0`) at `0x479C64`. Mismatch rejects. This does not identify the MCVar error `0x85000903`.

7. **The counter model is a replay relation, not a causal proof.** The preserved corpus validator reproduces 198 strict binary responses and 197/197 transitions with zero mismatches. Reviewer inspection confirms this is a strong within-run descriptive relation, but no IP/API/request-ID trace joins MCVar elements to writer invocations.

## Independent verification

- Developer artifacts: `DEVELOPER_NCDDE/annotated_assembly_report.md`, `DEVELOPER_NCDDE/response_counter_cfg.dot`, raw objdump/Rizin outputs, and `verify_old_bytes.py`.
- Reviewer artifact: `REVIEWER_INDEPENDENT_2026.md`.
- Old `ncdde.exe` byte assertions: **9/9 passed**; source literal assertion passed; old binary SHA-256 remained `40a030e0a7364aa358ae36494be1304810855997fb81804db91ea6fc05223916`.
- Runtime validator: exit 0, 104 steps/logs, 198 strict valid responses, 197 transitions, zero structural/counter mismatches.
- Existing combined unittest invocation from project root has an import-path defect for `test_real_input_corpus.py`; the directory-local corpus suite passes all 5 tests, and the validator tests pass. This remains a low-severity reproducibility issue, not a corpus failure.

## Remaining blockers

- Concrete `ReadVar -> PostMessageA/SendMessageA` callsite and argument mapping.
- Concrete request object allocation/vptr installation for the ReadVar path.
- Cross-process join from MCVar classic DDE window message to the NCDDE DDEML request and response buffer.
- Runtime attribution of the 198 captured packets to the old-image serializer.
- Origin/decoder of `0x85000903` and `0x81000303`.
- CacheDevice, timestamp semantics, and atomicity remain unproven.

## Scope

All work was offline and read-only. No Siemens binary was modified or executed, and no live industrial equipment was contacted. Solid graph edges are backed by instruction-level evidence; dashed edges represent unresolved indirect or cross-module joins.
