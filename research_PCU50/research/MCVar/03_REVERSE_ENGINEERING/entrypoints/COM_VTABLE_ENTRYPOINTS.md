# Stage 16.7 COM vtable entrypoint recovery

## Scope and binary identity

Offline static analysis only. Inputs were not modified.

| Build | Image | SHA-256 | PE base |
|---|---|---|---|
| old | `/root/PL/PCU_old/H/mmc2/MCVar.dll` | `43a5c1991d98b6b6e155233a0114d7ff72bf4dec7edf58d0607da501e7d98712` | `0x10000000` |
| new | `/root/PL/PCU_new/C/RECYCLER/S-1-5-21-4025392478-4199590385-3038547483-1005/Dc28/files/F/mmc2/MCVar.dll` | `5e7d955ebe7cfd52424b04e91471b7408f42bf6cc427e3d94c50bc7f4428c24a` | `0x10000000` |

Each image is PE32/i386. Old sections: `.text` RVA `0x1000`, size `0x2b000`; `.rdata` RVA `0x2c000`, size `0x4000`; `.data` RVA `0x30000`, raw/virtual sizes `0x8000/0xa000`. New sections: `.text` RVA `0x1000`, size `0x2c000`; `.rdata` RVA `0x2d000`, size `0x4000`; `.data` RVA `0x31000`, raw/virtual sizes `0x8000/0xa000`.

## ABI slot calculation

The Stage16.5 typelib records independently give both `IVar` and `IVar2` 12 methods with matching order. Both inherit `IDispatch`. Thus method slots are zero-based COM slots: IUnknown `0..2`, IDispatch `3..6`, and the listed IVar methods start at slot 7. The target ABI slot indices are `ReadVarAsync=9`, `ReadVarCyclic=11`, `RemoveCyclicVariables=12`, and `CalculateRequestRates=18`. These numbers identify ABI positions only, not concrete implementation addresses.

## Recovery result

The requested concrete COM entrypoints are **not established** from available static evidence. I found no initialized `.rdata` run of code pointers. The only apparent `.data` runs of code-range values in either file decode as repeated relocation-placeholder-like values, not candidate interface arrays. Name-string cross references and decorated labels do not prove an address is stored in an IVar/IVar2 slot. Constructor/interface pointer provenance connecting a particular `this` subobject to a specific IVar or IVar2 vtable array was not recovered.

Accordingly the target slot addresses and slot pointer values remain `null` in `VTABLE_MAP.json`. This is deliberate: assigning the `public_virtual` label address or the logging-string caller as the slot entry would confuse labels/callers with actual vtable entrypoints.

## Candidate and overlap evidence

Stage16.6 corrected boundaries identifies old `0x1000d28a` and new `0x1000d39c` as ReadVarAsync(IVar2) entry candidates, with matching 28-byte raw prefixes `85c059744f8b4df08bd3c1e204f7d98d941588b1ffff8d75b41bc923ca51`. It separately marks old `0x1000d3f6` / new `0x1000d508` as superseded overlapping labels, not independently proven thunks. These are body/boundary observations and do not establish which interface slot points to them.

Old disassembly around `0x1000c400` shows the `IVar::ReadVarAsync` diagnostic string at `0x1000c458` pushed from a larger body, not an entrypoint proof. The `IVar::RemoveCyclicVariables` string is referenced in the larger code near `0x10010c1d`; `ReadVarCyclic` diagnostics are likewise within code bodies. The `CalculateRequestRates` diagnostic caller around `0x100118c4` occurs in mixed/uncertain disassembly and is not accepted as a function boundary. In new, diagnostic code at `0x10010c02` is labelled ReadVarCyclic while including a RemoveCyclicVariables string push; this demonstrates why labels/string references alone are unsafe evidence.

## Evidence strength and next boundary

ABI order is established from `stage16_5/abi/typelib_abi_records.json`. Image identity, PE sections, and the ReadVarAsync candidate/overlap distinction are established from SHA-256 and Stage16.6 boundary records. Exact IVar/IVar2 vtable arrays, vtable slot pointer values, and constructor stores assigning those arrays to interface subobjects remain unresolved. No Windows execution, collector, DDE, source archives, or production modifications were used.
