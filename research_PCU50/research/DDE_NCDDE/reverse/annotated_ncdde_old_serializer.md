# Fresh old `ncdde.exe` response/counter reverse-engineering pass

## Scope and reproducibility

- **Input (read-only):** `/root/PL/PCU_old/H/mmc2/ncdde.exe`
- **Image base:** `0x00400000`; PE32/i386; timestamp `Tue Nov 2 06:29:03 2004` from fresh `objdump -x`.
- **Fresh tools:** GNU `objdump -Mintel -d` and `rizin` (`ii`, `axt`, `pd`). No execution of the vendor binary.
- **Artifacts:** every file in this directory is newly created; no binary or prior phase11 artifact was changed.
- **Raw evidence:** `objdump_response.txt`, `objdump_producer_serializer.txt`, `objdump_forward_create.txt`, `rizin_response.txt`, `rizin_serializer.txt`, `rizin_imports.txt`, `old_sha256.txt`.
- **CFG/data flow:** `response_counter_cfg.dot`.

## Verified dispatch edge: `0x448AC0 -> 0x449265`

Fresh objdump bytes at `0x449175`:

```
449175: 2d b0 20 00 00       sub eax,0x20b0
44917a: 0f 84 e5 00 00 00    je  449265
```

Thus transaction `0x20B0` reaches `0x449265`. At `0x449265`:

```
449265: a0 16 6d 4a 00       mov al,[0x4a6d16]
44926a: 84 c0                  test al,al
44926c: 0f 85 e1 07 00 00     jne 449a53
449272: 8b 75 0c              mov esi,[ebp+0xc]
449275: 83 fe 01              cmp esi,1
449278: 74 59                 je 4492d3
44927a: ... configured format WORD [0x499950] ...
449287: 83 fe 07              cmp esi,7
```

Here `wFmt` is reconstructed as the request argument `[EBP+0x0C]`; `0x449265` is not a universal success path because the global gate at `0x4A6D16` can branch to `0x449A53`.

## Format branches and item resolution

- Format `1` branches to `0x4492D3`.
- The configured format is loaded from `WORD [0x499950]` and also branches to `0x4492D3` when equal.
- Format `7` (`CF_OEMTEXT`) compares the current item handle `[0x486864]` against `[0x4A6D18]`:

```
44928c: a1 64 68 48 00       mov eax,[0x486864]
449291: 8b 0d 18 6d 4a 00    mov ecx,[0x4a6d18]
449297: 50                    push eax
449298: 51                    push ecx
449299: e8 88 dc 01 00        call 0x466f26
44929e: 85 c0                 test eax,eax
4492a0: 0f 85 ad 07 00 00     jne 0x449a53
```

Rizin independently reports `DdeCmpStringHandles` at `0x466f26` (IAT-backed call target). Equality reaches the special response; inequality reaches rejection/cleanup. Other formats call the request/item path beginning at `0x4492C7`/`0x4492D3` and eventually the producer path when guards permit.

## Producer and serializers

Fresh bytes establish the direct/thunk chain:

```
0x4493D4: e8 d4 8d fb ff       call 0x4021ad
0x4021AD: e9 8e 82 04 00       jmp  0x44a440
```

At `0x44A440`, producer logic checks object/format state and resolves an item. It has a format-2 fast path and fallback producer call. The guarded initialization branch at `0x44A4F1` reaches `0x44A5A1`; it is not unconditional.

`0x44A5A1` is the serializer/buffer initializer. Exact bytes:

```
44a5a1: 8b 4c 24 18          mov ecx,[esp+0x18]   ; iteration/count input
44a5a5: ba 01 00 00 00       mov edx,1
44a5aa: 66 c7 05 d0 6b 48 00 14 00 ; WORD [0x486BD0]=0x14
44a5b3: 66 89 15 d2 6b 48 00       ; WORD [0x486BD2]=1
44a5ba: c7 05 e0 6b 48 00 f9 f8 f7 f6 ; DWORD [0x486BE0]=0xF6F7F8F9
44a5c4: 66 c7 05 d6 6b 48 00 00 00  ; WORD [0x486BD6]=0
```

It loops over producer calls through `0x40203B` (`0x44A730` target by thunk). Return values `-3`, `-2`, and `0` branch to distinct failure/cleanup returns; positive values continue. For a one-valued mode it appends a NUL and advances the cursor.

At `0x44A730`, the fresh disassembly shows indexed item resolution:

```
44a73a: mov ecx,[eax+0xa6]
44a745: mov edx,[ecx+eax*4]
44a74c: mov ebx,[edx+0x36]
44a74f: mov edx,[ecx+4]
44a752: mov edi,[edx+eax*4]
44a75d: add edi,4
```

It derives a mode/length state from item and producer structures, then iterates output. This supports producer-to-serializer/data-flow linkage but does not identify high-level field names without runtime/type information.

## Counter writer and exact failed-request branches

The packed sequence writer is at `0x44AA8A`:

```
44aa8a: a0 84 68 48 00          mov al,[0x486884]
44aa92: 66 0f b6 4c 24 20       movzx cx,byte [esp+0x20]
44aa98: 8a d0                   mov dl,al
44aa9a: c1 e2 08                shl edx,8
44aa9d: 03 d1                   add edx,ecx
44aaa3: 66 89 15 d6 6b 48 00   mov [0x486bd6],dx
44aab4: fe c0                   inc al
44aab7: a2 84 68 48 00          mov [0x486884],al
```

Therefore the exact counter update is an **8-bit modulo-256 increment** of `[0x486884]`, and the stored WORD at `[0x486BD6]` is `(old_global_byte << 8) | stack_byte`. The update is reached only after the guarded output/producer path; it is not executed on every request.

The relevant failure/control returns are exact:

- producer/worker `-3` at `0x44A612` → `0x44A659` → return `0`;
- `-2` at `0x44A617` → `0x44A663` → return `0xFFFFFFFE`;
- worker `-3` at `0x44A902` → `0x44ABD5`, clears output handle and returns `-3` or `-2` depending on `[item+7]`;
- worker `-2` at `0x44A90B` → `0x44ABC8`, returns `0xFFFFFFFE`;
- worker result `-1` at `0x44A914` enters special handling; if `[item+7] != 2`, `0x44A921` branches to `0x44AB67` and returns `0`; otherwise it synthesizes a fallback data operation and continues.

The success/continuation edge at `0x44A953` tests result `1`; it clears `DWORD [ESI]` before the failure/non-success split. The counter writer is therefore not evidence of a successful DDE handle by itself.

## Buffer forwarding and DDE handle creation

At the flush path:

```
44a66e: 2d d0 6b 48 00       sub eax,0x486bd0       ; cursor - buffer base
44a673: 51                    push ecx
44a674: 50                    push eax               ; byte count/offset-derived value
44a675: 68 d0 6b 48 00       push 0x486bd0          ; buffer base
44a67f: 55                    push ebp
44a680: e8 73 6c fb ff        call 0x4012f8
```

The serializer flush at `0x44AB2B` calls the same forwarding thunk. The thunk target is `0x44AD50`.

At `0x44AD50`, mode selects an internal destination offset (`object+0x8A` for mode `1`, otherwise `object+0x8E`), and format `2` has an additional gating test. Existing destination handles use `DdeAddData` at `0x44ADDE` or later paths. The creation path is distinct:

```
44ae0a: 8b 15 c0 6c 4a 00    mov edx,[0x4a6cc0] ; idInst
44ae12: ...                  ; hszItem=[0x486864]
44ae1b: 50                    push afCmd (derived setne)
44ae1c: 57                    push edi            ; wFmt
44ae1d: 51                    push ecx            ; hszItem
44ae1e: 6a 00                 push 0               ; cbOff
44ae20: 55                    push ebp            ; cb
44ae21: 56                    push esi            ; pSrc
44ae22: 52                    push edx            ; idInst
44ae23: e8 2e c1 01 00        call 0x466f56
```

Rizin reports the indirect call target `0x466f56` as `USER32.dll!DdeCreateDataHandle` through IAT address `0x006C6338`. Reverse-push reconstruction is therefore:

`DdeCreateDataHandle(idInst, pSrc, cb, cbOff, hszItem, wFmt, afCmd)`.

This callsite is not the `DdeAddData` path.

## Dedicated OEMTEXT response

The equality path at `0x4492A6` reconstructs:

- `idInst = [0x4A6CC0]`
- `pSrc = 0x479C64`, bytes `4e 63 64 64 65 00` (`Ncdde\0`)
- `cb = 6`
- `cbOff = 0`
- `hszItem = [0x486864]`
- `wFmt = 7`
- `afCmd = 0` (`EDI` is zero on this dispatch path)

The result is a six-byte OEMTEXT data handle on the item-equality branch. It does not prove all format-7 requests take this path, because the item comparison and global gates are explicit.

## Cross-check and limits

- Cross-tool check: GNU objdump and rizin independently decode the `0x449175` transaction branch, `0x449287` format-7 test, serializer/forwarding callsites, and the `USER32!DdeCreateDataHandle` import identity. The exact bytes are preserved in the objdump artifacts.
- No Ghidra headless run was available/necessary in this environment; the second-tool requirement is satisfied by rizin against objdump.
- No dynamic execution, debugger trace, DDE client, Windows USER32 behavior, or MCVar causality was established.
- Candidate VAs are valid only for this old image/base; no new-image address equivalence is inferred.
- Calls through internal virtual tables/thunks are identified by machine-code targets, but their semantic names beyond the DDE imports remain inferred from data flow.
- The counter’s runtime frequency, concurrency behavior, and external consumer semantics are not proven statically.
