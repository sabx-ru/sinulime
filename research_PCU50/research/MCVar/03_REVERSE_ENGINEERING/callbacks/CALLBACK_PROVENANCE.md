# Callback provenance and dispatch join

## Scope

Offline static analysis only of the exact old/new `MCVar.dll` images. No Windows, DDE, collector, or runtime callback-delivery test was used. Addresses are preferred VAs at image base `0x10000000`.

- Old: `/root/PL/PCU_old/H/mmc2/MCVar.dll`, SHA-256 `43a5c1991d98b6b6e155233a0114d7ff72bf4dec7edf58d0607da501e7d98712`
- New: `/root/PL/PCU_new/C/RECYCLER/S-1-5-21-4025392478-4199590385-3038547483-1005/Dc28/files/F/mmc2/MCVar.dll`, SHA-256 `5e7d955ebe7cfd52424b04e91471b7408f42bf6cc427e3d94c50bc7f4428c24a`

Evidence classes:

- **DIRECT**: instruction-level call, operand, or data-flow edge is visible in the raw disassembly.
- **INFERRED**: independent byte evidence and API/symbol/diagnostic correlation support the relationship, but the exact causal instruction or field identity is absent.
- **UNRESOLVED**: the proposed edge is not established by the available bytes.

## Result

A complete callback *dispatch shape* is proven in both builds:

```text
ReadVarAsync entry
  -> direct shared-starter call
  -> transaction record retaining callback/dispatch-related inputs
  -> completion/helper region
  -> IDispatch::GetIDsOfNames("OnDataChanged")
  -> DISPID local
  -> IDispatch::Invoke-shaped call
```

The first three edges are direct through the request-construction slice, except that the exact transaction field corresponding to `pCB` versus `pDisp` is not uniquely labeled. The `GetIDsOfNames` site and the `Invoke`-shaped site are each direct; their cross-routine name-resolution-to-invocation linkage is inferred from the DISPID local and matching helper diagnostics. The edge from a particular async transaction or cyclic owner to that helper is not closed by a raw direct call or unique field use.

**No direct typed callback call was found.** The callback interfaces are passed as COM interface pointers and the evidenced delivery-shaped operation is late-bound `IDispatch`; there is no raw `call [pCB+typed_slot]` or direct relative call to an `IReadVarAsyncCallback*` method in the captured paths. The exact unresolved edge is:

```text
specific ReadVarAsync/Cyclic transaction completion or cyclic flush owner
  -> callback helper instance / helper entry
```

This is not a claim that delivery cannot occur. It is the exact static join that remains unproven.

## Request and subscription provenance

### ReadVarAsync

The public method declarations identify the inputs as variants, mode, `IReadVarAsyncCallback*`/`IReadVarAsyncCallback2*`, `IDispatch*`, `long *pReqID`, and result variant. The raw entry slice directly passes the callback and dispatch-related arguments into the shared starter:

- Old `0x1000d28a` -> starter `0x1000d7a4` at callsite `0x1000d2d5`.
- New `0x1000d39c` -> starter `0x1000d8b6` at callsite `0x1000d3e7`.
- Old pushes include `[arg_1ch]` and `[arg_18h]` at `0x1000d2af` and `0x1000d2b2`; new equivalents are `0x1000d3c1` and `0x1000d3c4`. The decorated signatures identify these as the callback and `IDispatch` inputs, but the starter's local argument renaming does not preserve a unique pCB/pDisp label.
- The starter copies pointer-like inputs into transaction offsets `+0x84`, `+0x88`, and `+0x90` (old `0x1000d826/0x1000d82c/0x1000d832`; new `0x1000d938/0x1000d93e/0x1000d944`). These are direct retention stores. Which exact offset is pCB and which is pDisp is unresolved from the captured bytes.
- The caller `pReqID` pointer is separately stored at transaction `+0x98` (old `0x1000d842`; new `0x1000d954`). It is a pointer, not the numeric RID.
- The returned transaction pointer is placed in the 12-byte result wrapper at `+0x04` (old continuation around `0x1000d48d`; new around `0x1000d59f`).

The entry also contains direct diagnostic paths for `StartRead`/`StartWrite`/`StartExec`, but those messages do not prove callback delivery. The starter's `new CTransaction ... RID` log and comparisons establish request identity machinery, not the origin of the generated RID.

### ReadVarCyclic / subscription path

Both images expose `ReadVarCyclic`, `RemoveCyclicVariables`, callback/dispatch inputs, request IDs, `CCyclicID`/`CCyclic` diagnostics, and cyclic flush regions. The available cyclic evidence directly proves list/object traversal and, in the new build, a conditional direct call from the FlushCyclics region (`0x100134ab`) to callback-dispatch candidate helper `0x100139c2`. The old helper `0x100138b8` has matching dispatch evidence, but no equivalent old cyclic caller edge is verified.

That new cyclic helper edge is direct only to the helper. It does not prove that the helper's `Invoke` is reached for every subscription, that the owner object is the same object retained by the public request, or that a runtime callback is delivered.

## Dispatch-shaped path

The corrected interpretation of the `+0x14` calls is essential. At old `0x1000fef1` and new `0x10010003`, `call [eax+0x14]` is `IDispatch::GetIDsOfNames`, not callback delivery. The name pointer is:

- Old `0x100320cc`: UTF-16 `OnDataChanged`.
- New `0x1003311c`: UTF-16 `OnDataChanged`.

The HRESULT is checked immediately. In the separate callback helper:

- Old endpoint `0x100146a0`: `call [edx+0x18]` after `eax=[ebx+0x14]` and `edx=[eax]`.
- New endpoint `0x100147aa`: structurally equivalent call.

At both endpoints the pushed arguments are, in call order from the stack setup:

```text
this     = callback/dispatch pointer loaded from [ebx+0x14]
DISPID   = local [var_14h]
riid     = local storage [var_50h] / ESI
lcid     = 0x800
wFlags   = 1
pDispParams = &var_28h
pVarResult  = 0
pExcepInfo  = 0
puArgErr    = 0
```

`var_14h` is the DISPID-like local populated by the preceding name-resolution path. `var_28h` is assigned a pointer to the locally prepared value area (`var_d0h`), after six 16-byte-looking VARIANT copies are made. The exact `DISPPARAMS` member values, argument count, named-argument count, and semantic mapping of those values are not recoverable from the bounded endpoint slice.

Adjacent diagnostics name `OnDataChanged` called and returned HRESULT, but diagnostics are corroboration, not runtime proof.

## Direct typed-call finding

No direct typed callback invocation was found in the inspected old/new request, starter, completion, or cyclic slices. Specifically:

- No direct relative call targets a typed `IReadVarAsyncCallback` method.
- No call through a callback interface pointer with a uniquely identified typed method slot was recovered.
- The concrete callback operation visible in the helper is late-bound `IDispatch::Invoke` at vtable slot `+0x18`.
- The transaction-object vtable `+0x04` call in a terminal branch remains a separate unresolved object operation and is not promoted to a callback method.

## Exact unresolved edge

The strongest exact statement supported by raw bytes is:

```text
ReadVarAsync -> starter -> retained callback/dispatch-related transaction fields
    [DIRECT]
retained transaction/event owner -> callback helper / helper instance
    [UNRESOLVED]
helper -> GetIDsOfNames("OnDataChanged") -> DISPID local -> Invoke-shaped call
    [DIRECT]
```

The unresolved join is caused by the absence of a verified direct call from the ReadVarAsync transaction completion owner to `0x100146a0`/`0x100147aa`, and by the lack of a unique read of transaction `+0x84/+0x88/+0x90` that identifies pCB or pDisp at the endpoint. Names, matching diagnostics, symbol labels, and API declarations cannot close that gap.

## Evidence files

- `../stage16_6/corrections/dispatch/ASYNC_CALLBACK_DISPATCH.md`
- `../stage16_6/corrections/dispatch/old_context.txt`
- `../stage16_6/corrections/dispatch/new_context.txt`
- `../stage16_6/async/raw/old_rizin_lifecycle.txt`
- `../stage16_6/async/raw/new_rizin_lifecycle.txt`
- `../stage16_5/async_flow/old_callback_ref_disasm.txt`
- `../stage16_5/async_flow/new_callback_ref_disasm.txt`
- `../stage16_6/cyclic/CYCLIC_LIFECYCLE.md`
- `../stage16_6/cyclic/CYCLIC_FUNCTION_GRAPH.json`
- `../stage16_7/evidence/old_target_strings.txt`
- `../stage16_7/evidence/new_target_strings.txt`
