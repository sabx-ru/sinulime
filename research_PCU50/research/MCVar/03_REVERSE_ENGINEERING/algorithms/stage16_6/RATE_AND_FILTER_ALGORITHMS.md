# MCVar rate and filter algorithms: static evidence boundary

## Scope

Offline static analysis only. No Windows execution, client/collector, DDE, or PCU interaction. Names are used to locate code but are not treated as semantic proof. Binary identity was independently hashed:

- Old: `/root/PL/PCU_old/H/mmc2/MCVar.dll`, SHA-256 `43a5c1991d98b6b6e155233a0114d7ff72bf4dec7edf58d0607da501e7d98712`, PE image base `0x10000000`.
- New: `/root/PL/PCU_new/C/RECYCLER/S-1-5-21-4025392478-4199590385-3038547483-1005/Dc28/files/F/mmc2/MCVar.dll`, SHA-256 `5e7d955ebe7cfd52424b04e91471b7408f42bf6cc427e3d94c50bc7f4428c24a`, image base `0x10000000`.

The relevant public routines are located by Rizin analysis at old `CalculateRequestRates` VA `0x10012868`, new `0x1001297a`; old `normalizeUpdateRate` VA `0x100129a2`, new `0x10012ab4`. These symbol starts are not reliable instruction boundaries: disassembly at each starts with invalid-looking code and skips into a loop already in progress. Rizin also labels the helper body at `0x10012914` old / `0x10012a1e` new as a different routine; its SAFEARRAY operations interleave with the rate routine. Therefore conclusions below cite valid interior instruction ranges, not function-start pseudocode.

## Proven observations

### Requested/revised rate entry and SAFEARRAY shape

The typelib records for both IVar and IVar2 expose `CalculateRequestRates` with a VARIANT input and VARIANT-pointer output (see `stage16_5/abi/typelib_abi_records.json`, method records; decoded declarations are summarized in `stage16_5/abi/README.md`). This establishes ABI shape only, not rate units or policy.

In old code, `0x100128d3-0x10012904` and corresponding new code `0x100129dd-0x10012a0e` call `SafeArrayAccessData` on output/input descriptors, populate a descriptor's type word with `0x200b`, and call `SafeArrayGetDim` on an array in a cleanup/error path. The descriptor type is literal evidence; no semantic name is inferred from it. Earlier interior loop instructions use byte loads from array data and write 16-bit words into another accessed array.

At old `0x10012869-0x10012897` (new `0x1001296f-0x100129a1`), the loop loads one byte at `[array_data + eax]`, ANDs it with a byte selected from a stack-resident table, then `neg` and `sbb reg,reg` produce either `0x0000` or `0xffff`; it stores that word at `[output_data + 2*index]`. The loop bounds include an 8-iteration comparison. A second loop (old `0x100128ab-0x100128d1`, new `0x100129b5-0x100129db`) repeats the same byte-mask -> 0/−1 word mapping while advancing its destination by 2 bytes. These operations prove a byte-mask expansion into 16-bit all-zero/all-one values. The use and source construction of the masks are not reliably recovered, so this is not identified as a particular filter or rate policy.

### Helper variant and array handling

The helper's valid old block begins `0x10012914`, new `0x10012a1e`. It compares VARTYPE low 12 bits (`and ax,0xfff` / `and dx,0xfff`) and branches on the values, rejecting/handling zero and one cases at old `0x1001292e-0x1001295c` (new `0x10012a38-0x10012a66`). It tests flag bits `0x20` and `0x40` in each variant type byte and conditionally loads pointers (`old 0x10012962-0x1001299c`; new `0x10012a6c-0x10012aa6`). A later block calls `SafeArrayCopyData` (old `0x100129aa-0x100129b1`; new `0x10012ab4-0x10012abb`). On failure/nonzero HRESULT, it branches into `SafeArrayCopy`/`SafeArrayPutElement` iteration, with one branch selected when VARTYPE low 12 bits equal `0x08` and another using a different element address step (old `0x100129dc-0x10012a88`, new `0x10012ae6-0x10012b92`). This proves type-dependent SAFEARRAY copying and element insertion. It does not prove that the helper computes, clamps, rounds, or normalizes scalar update rates.

## Deadbands and CriticalValues

The type library declares both as VARIANT inputs to `ReadVarCyclic`; this only proves interface slots. Prior static lifecycle evidence (`stage16_5/cyclic_flow/CYCLIC_LIFECYCLE.md`) reports a `StartCyclic` diagnostic formatting stored fields including deadband, requested update rate, and a critical flag, but the diagnostic labels and stored fields do not establish filtering behavior.

No reliable instruction sequence from either exact binary has yet been isolated that consumes deadband and compares current versus prior values, nor a sequence that consumes CriticalValues and compares a value to a threshold. Consequently these remain unresolved: scalar/array interpretation, element type conversion, comparison operator, absolute/relative delta, equality boundary, NaN/error handling, per-variable versus per-subscription state, threshold direction, hysteresis, and whether critical values alter delivery at all. Parameter names are not evidence for any of these behaviors.

## Old/new comparison

Both binaries have the same high-level observed interior pattern: bytewise AND against a stack-resident mask followed by `neg`/`sbb` and a 16-bit 0/−1 store; SAFEARRAY access/copy/element operations; low-12-bit VARTYPE checks and flag-bit tests in the adjacent helper. Addresses differ (public entry old/new `0x10012868`/`0x1001297a`; helper old/new `0x10012914`/`0x10012a1e`). Misalignment at public symbol starts and overlapping function analysis mean this evidence is not sufficient to assert identical complete algorithms or a semantic delta between versions. The entry bytes and complete function-level control flow were not established as matched.

## Explicit blockers / no regression model

- Recover correct instruction boundaries and complete CFG for `CalculateRequestRates` and `normalizeUpdateRate` in each image, including prologue, arguments, calls, and return paths. Current Rizin analysis reports function sizes 136/155 bytes and 136/147 bytes respectively but its decoded entry bytes are invalid/misaligned; helper code overlaps/interleaves.
- Identify stack-table construction and exact array bounds/element mapping to establish what the 8-mask loop transforms.
- Trace the actual `ReadVarCyclic` caller/helper paths passing rates, deadbands, and critical values into stored record fields and any comparison/delivery path.
- Recover real deadband and critical-value conversion/comparison branches from valid instructions before defining pure logic.

No Linux regression check is appropriate: none of the scalar rate normalization, deadband, or critical-value semantics is fully recovered. The only safely translatable pure fragment is the literal byte-mask-to-word operation, but its role as requested/revised-rate or filter behavior is not established, so it is deliberately not presented as an algorithm implementation.
