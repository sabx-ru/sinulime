# Phase 11 Track B — independent NCDDE serializer / OEMTEXT / error verification

## Verdict

**Verified with limitations.** Static old-image facts are independently reproduced from raw PE bytes. The serializer's guarded buffer construction, packed sequence store, forwarding wrapper, and eligible `DdeCreateDataHandle` call are **high confidence**. The special `CF_OEMTEXT` response is **high confidence**. MCVar-to-NCDDE runtime causality, per-capture attribution, and the origin/decoder of `0x85000903` are **not verified**.

Scope was read-only static analysis of `/root/PL/PCU_old/H/mmc2/ncdde.exe`, plus literal/immediate scans of the old/new `ncdde.exe` and `MCVar.dll` copies. No vendor binary was executed; no live/hash work was performed; immutable inputs were not modified.

## Exact-byte findings

All addresses below are VAs for ImageBase `0x00400000`; raw VA/RVA/bytes are in `FUNCTIONS/reviewer_track_b_raw.asm`, and byte assertions are in `FUNCTIONS/reviewer_track_b_assertions.py`.

| Edge | Exact bytes / decoded operation | Confidence |
|---|---|---|
| Receiver `0x448AC0` → request | `0x449175: 2d b0 20 00 00`; `0x44917a: 0f 84 e5 00 00 00` — transaction `0x20B0` reaches `0x449265`. `0x449272: 8b 75 0c` loads `wFmt=[EBP+0x0C]`. | **High** |
| Normal request → producer | `0x4493d4: e8 d4 8d fb ff` calls thunk `0x4021AD`; thunk bytes `e9 8e 82 04 00` target `0x44A440`. Guarded path, not universal. | **High** |
| Header/buffer init | `0x44A5AA: 66 c7 05 d0 6b 48 00 14 00` → WORD `[0x486BD0]=0x14`; `0x44A5B3: 66 89 15 d2 6b 48 00` → WORD `[B+2]=1`; `0x44A5BA: c7 05 e0 6b 48 00 f9 f8 f7 f6` → bytes `F9 F8 F7 F6` at `B+0x10`; `0x44A5C4: 66 c7 05 d6 6b 48 00 00 00` clears WORD `[B+6]`. | **High** |
| Producer → serializer | `0x44A60A: e8 2c 7a fb ff` calls thunk `0x40203B`; thunk `0x40203B: e9 f0 86 04 00` targets `0x44A730`. | **High** |
| Packed sequence write | `0x44AA8A: a0 84 68 48 00` reads byte `[0x486884]`; `0x44AA92: 66 0f b6 4c 24 20` reads a separate stack byte; `0x44AAA3: 66 89 15 d6 6b 48 00` stores DX to WORD `[B+6]`. Therefore `[B+6]` is the stack byte and `[B+7]` is the pre-increment global byte. `0x44AAB4: fe c0` increments AL; `0x44AAB7: a2 84 68 48 00` stores it back. | **High** for bytes/packing; **medium** for runtime frequency/semantics |
| Buffer forwarding | `0x44A66E: 2d d0 6b 48 00` computes cursor−`B`; `0x44A675: 68 d0 6b 48 00` pushes `B`; `0x44A680: e8 73 6c fb ff` calls thunk `0x4012F8`, which targets `0x44AD50`. Serializer flush also calls the same thunk: `0x44AB2B: e8 c8 67 fb ff`. | **High** |
| Handle creation | `0x44AE23: e8 2e c1 01 00` calls `0x466F56`; thunk bytes `ff 25 38 63 6c 00` indirect through IAT `0x006C6338`, independently parsed as `USER32!DdeCreateDataHandle`. | **High** |

The wrapper's normal seven-argument order is `(idInst, pSrc, cb, cbOff, hszItem, wFmt, afCmd)` with reverse x86 pushes. At the `0x44AE23` path, the raw pushes are `afCmd`, `EDI` format, `[0x486864]` item, `0`, `EBP` length, `ESI` source, `[0x4A6CC0]` instance. Existing/reusable handles can instead use `DdeAddData` paths (`0x44ADDE`, `0x44AE5C`); do not collapse those paths into creation.

## CF_OEMTEXT special response

At request dispatch, `0x449287: 83 fe 07` tests format 7 (`CF_OEMTEXT`), and `0x449299` calls the `DdeCmpStringHandles` thunk (`0x466F26`, IAT `0x006C631C`) to compare `[0x4A6D18]` with current item `[0x486864]`. A nonzero comparison branches to rejection/zero return; equality reaches the special handle call.

Exact callsite bytes:

```
0x4492AC  a1 c0 6c 4a 00       mov eax,[0x4A6CC0]
0x4492B1  57                   push edi        ; afCmd = 0
0x4492B2  56                   push esi        ; wFmt = 7
0x4492B3  52                   push edx        ; hszItem = [0x486864]
0x4492B4  57                   push edi        ; cbOff = 0
0x4492B5  6a 06                push 6          ; cb = 6
0x4492B7  68 64 9c 47 00       push 0x479C64   ; pSrc
0x4492BC  50                   push eax        ; idInst
0x4492BD  e8 94 dc 01 00       call 0x466F56
```

Raw source bytes at `0x479C64` are exactly `4e 63 64 64 65 00` (`Ncdde\0`). This proves a six-byte OEM-text response on the equality path, not an empty handle and not the normal binary serializer response. **Confidence: high.** It does not prove that every OEM request reaches equality or that a preserved client error came from the rejection branch.

## `0x85000903` search and boundary

The focused scan covered exactly four files: old/new `ncdde.exe` and old/new `MCVar.dll`. It searched for:

- little-endian DWORD bytes `03 09 00 85`;
- big-endian bytes `85 00 09 03`;
- ASCII `85000903`;
- UTF-16LE `85000903`.

All four files returned **zero matches** (`FUNCTIONS/reviewer_track_b_error_literal_scan.json`). An additional executable-section immediate scan for `0x85000903`, `0x85000900`, and `0x85000000` also returned no candidates (`FUNCTIONS/reviewer_error_cleanup_audit.asm`).

This is a **high-confidence negative literal/immediate result within the stated files/scans**, not proof that the value cannot be constructed arithmetically, looked up, propagated from another module, or returned by an external/API boundary. The preserved corpus records one MCVar slot with `0x85000903`; that observation is separate from static origin proof. OEM rejection must not be identified with this error without runtime/client evidence. **Origin confidence: not established.**

## Executed checks

`python3 FUNCTIONS/reviewer_track_b_verify.py` completed and regenerated the raw disassembly/literal scan. `python3 FUNCTIONS/reviewer_track_b_assertions.py` completed:

```
PASS 18 instruction-byte assertions; 2 import identities; six-byte source; exhaustive 65536-pair packing model; byte wrap model
PASS header prefix is WORD 20 / WORD 1; DWORD == 20 predicate rejects this prefix
```

These checks validate preserved bytes and an isolated packing model; they do not execute vendor code or establish dynamic branch occurrence.
