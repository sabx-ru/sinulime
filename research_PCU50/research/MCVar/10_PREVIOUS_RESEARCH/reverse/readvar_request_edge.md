# Phase 11 Track A: MCVar ReadVar request/transport boundary

## Status

Static instruction analysis only; no vendor executable was run and no live target was accessed. Original `PCU_old` inputs and existing evidence were left untouched. This is an evidence checkpoint, not a completed transport reconstruction.

## Corrected chain and evidence

Primary byte evidence is `research/logs_asmb/consolidation_architect.asm`, generated from original `PCU_old/H/mmc2/MCVar.dll` section bytes. Preferred image base is `0x10000000`; `.text` begins at VA `0x10001000`.

- Usable ReadVar body starts at `0x1000BC30` (`push ebp; mov ebp,esp; sub esp,0x3c`). Export-labelled `0x1000BC74` is interior code (`mov word ptr [edi],si`), not its function entry.
- At `0x1000BC3C`, interface `this` is adjusted by `-0xc` into `ebx`; `0x1000BC45` calls `0x10014C8C` with that pointer and literal `0xc`.
- The body constructs stack VARIANT-like records and calls `0x1000C532` at `0x1000BD47`. That function starts a `0xe8`-byte frame, saves controller `this` from `ecx`, and handles several arguments/stack records. This is a concrete request-construction candidate, not yet a proven submission path.
- `0x1000BDDC -> 0x10014CBE` is scope cleanup. It restores `[object+0x24]` and calls `[object-vptr+8]` at `0x10014CE2`. This is lifetime cleanup, not request submission.
- Old lifetime vptr candidates are `0x1002C5BC` and `0x1002C758`, installed at `0x10008EE3`/`0x10009637` and `0x100098D3`. Slot +8 targets are `0x100099D7 -> 0x10009783` and `0x10009A6D -> 0x100098FE`; these implement reference-count release/delegation. They are not the ReadVar transport edge.
- `0x10004CA7` is a separate switch method. In its `0x10004DD1` branch, object result from `0x10004AC8` is stored at `[ebp-4]`; `0x10004E2E` executes `call [edx+4]` with `edx=[esi]`, `ecx=esi`, and pushes the dereferenced result and zero. `esi` is that switch method's `this`. Slot target is unresolved.
- Re-decoding `0x10004AC8` shows a separate string/name preparation routine: reads field `[edi+0x48]`, invokes helper `0x10007A42`, then builds heap/string state with `0x100017B9`, allocator/import slots at `0x1002C060/05C`, and helper `0x1000576F`. It returns a prepared object/string candidate, not enough evidence to identify the vtable used at `0x10004E2E`.
- New-image `0x10007DBD` is cleanup per the independent review; do not label it decoder. No causal join between parser candidate, request-region vcall, and later DDE capture is established.

## Runtime evidence boundary

The existing consolidation note reports successful harness `IDispatch.Invoke` and separately a later `ncdde|machineswitch` 24-byte DATA_HANDLE. Neither record provides instruction pointer/vptr/packet mapping that ties that buffer to this ReadVar call. Keep them as distinct observations.

## Smallest unresolved edge and next slice

Resolve the concrete object returned by `0x10004AC8` in the `0x10004CA7` `0x10004DD1` branch; find its allocation/constructor and vptr write, decode the resulting slot +4, then inspect that callee. Separately continue within `0x1000C532` until the API/IPC submission and returned handle/buffer are explicit. A bridge requires concrete submission and correlated server/output-buffer evidence; current static analysis does not establish either.

## Tool execution note

SSH tiny command (`true`, timeout 10s) succeeded. `objdump`, `rizin`, Capstone 5.0.7 and `pefile` are available. One initial Capstone section extraction used an incorrect RVA/section accessor and returned empty output; corrected extraction used PE section file offsets and VA mapping. No 420-second waits were used.
