# Phase11 counter-causal model

## Boundary

This is a **runtime model**, not transport proof. It describes only the preserved Windows XP x86 session in `/root/PL/real_tests/logs/RUN_ALL_21704_14346.txt` and paired bin logs/captures. It does not establish deployed-module identity, live behavior, source freshness, or a complete client-to-server call edge.

## Observed packet model

All 198 valid binary captures use a packed WORD header:

| Offset | Width | Observation |
|---|---:|---|
| 0 | WORD | header length `0x0014` (20) |
| 2 | WORD | version/field `0x0001` |
| 4 | WORD | representation field; varies by payload |
| 6 | WORD | packed dynamic fields |
| 7 | BYTE | observed sequence byte |
| 12 | DWORD | payload byte count |
| 16 | 4 bytes | marker `F9 F8 F7 F6` |
| 20.. | variable | payload |

Thus `14 00 01 00` is WORD(20), WORD(1), and the whole DWORD at offset 0 is 65556. A DWORD==20 parser is a rejected hypothesis: it accepts zero real responses.

## Fitted transition relation

For each adjacent valid binary capture, including gaps containing failures or no MCVar call:

`delta(sequence) = (1 + sum(processed MCVar elements in strictly intervening runner steps)) mod 256`

The preserved ledger records **197 transitions and zero mismatches** in `/root/PL/research/phase11/REAL_INPUT_CORPUS/counter_transitions.json`. Accepted elements include valid, invalid, duplicate, and repeated items. The two rejected `SAFEARRAY(VARIANT)` shapes contribute zero processed elements. Representative nonzero bridges are 73->75: 1, 75->77: 5, 77->79: 20, 79->81: 5, 81->83: 3, 89->91: 40, 96->98: 20, 99->101: 20, and 101->103: 40; every listed delta is predicted exactly.

## Causal status

The data support a compact replay relation for this run. They do **not** prove that every accepted MCVar element caused one transport increment, that every captured item used the same serializer path, or that a request maps one-to-one to an observed server invocation. Static review found an old-image path that initializes WORD `0x14`, writes the marker at `B+0x10`, stores a packed dynamic WORD at `B+6`, exposes byte 7 as the pre-increment cursor byte, and post-increments a global cursor. Those facts are static disassembly evidence, not dynamic tracing.

The exact static references are preserved at `/root/PL/research/phase11/FUNCTIONS/reviewer_track_b_raw.asm`, `/root/PL/research/phase11/FUNCTIONS/reviewer_track_b_focus.asm`, and `/root/PL/research/phase11/UNRESOLVED_BOUNDARIES_REVIEWER_TRACK_B.md`.

## MCVar and timestamp limits

The runtime ledger reports 65 rounds, 606 requested, 604 processed, and 2 rejected shapes. Seven rounds have partial slot errors with zero Invoke HRESULT. All 63 accepted cache rounds return `pTimeStamps` as `VT_ERROR 0x80020004`, so no source timestamp is available. `SysTimeBCD` and OLE_DATE changes are dynamic values, not proof of freshness or transport timing.

## Reproduction boundary

The artifacts can be checked offline with `/root/PL/research/phase11/SCRIPTS/revalidate_latest_runtime.py` and the existing unit tests, but this refresh intentionally used the already preserved latest runtime results and did not re-run blocked tooling. The machine-readable source of truth is `latest_runtime_validation.json`; this document is its concise causal interpretation.
