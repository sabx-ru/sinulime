# Stage 16.6 Callback Dispatch Correction

## Corrected interpretation

At old `0x1000fef1` and new `0x10010003`, the instruction `call [eax+0x14]` is not an `OnDataChanged` invocation. On 32-bit `IDispatch`, offset `+0x14` is `GetIDsOfNames`; `Invoke` is at `+0x18`.

The complete old callsite pushes:

- `this = EDI`;
- `riid = 0x1002d6c8`;
- `rgszNames = &stack[0x10]`;
- `cNames = 1`;
- `lcid = 0x800`;
- `rgDispId = &stack[0x14]`.

Immediately before the call, the stack string pointer at `[ebp+0x10]` is set to `0x100320cc`, whose UTF-16 content is `OnDataChanged`. Therefore the direct conclusion is:

```text
validated callback-like object -> IDispatch::GetIDsOfNames("OnDataChanged") -> HRESULT check
```

The new callsite has the corresponding resources and is structurally equivalent. The previous statement “vtable slot `+0x14` directly invokes `OnDataChanged`” is superseded and retained only in historical evidence.

## What is proven after name resolution

The old path checks the `GetIDsOfNames` HRESULT at `0x1000fef4` and branches on failure. In a separate callback routine, the resolved output local is used in a later `IDispatch::Invoke`-shaped call:

```asm
1001468c: mov eax, [ebx+0x14]      ; callback/dispatch object
1001468f: push 0                  ; argErr
10014690: push 0                  ; excepInfo
10014691: push 0                  ; result
10014692: lea ecx, [var_28h]
10014695: mov edx, [eax]           ; vtable
10014697: push ecx                 ; DISPPARAMS*
10014698: push 1                   ; wFlags
1001469a: push 0x800               ; LCID
1001469b: push esi                 ; RIID / IID_NULL storage
1001469c: push [var_14h]           ; DISPID from name-resolution path
1001469f: push eax                 ; IDispatch this
100146a0: call [edx+0x18]          ; IDispatch::Invoke-shaped call
```

The new build has the structurally equivalent call at `0x100147aa`. Nearby diagnostics log `Dispatch "OnDataChanged" called` and then log the returned HRESULT. This proves a static `GetIDsOfNames` -> DISPID local -> `Invoke`-shaped call sequence in the callback routine. It does not prove that a real user callback object is reached, that the call succeeds at runtime, or that this routine is reached by every `ReadVarAsync` or cyclic request. The `DISPPARAMS` contents and exact callback source remain unresolved.

The earlier `ChangeArrayType` path still ends in `ExecuteAsync` machinery at old `0x1000ff0e` / the corresponding new path; that site alone remains name resolution and is not the callback delivery path.

## Required status

- `GetIDsOfNames("OnDataChanged")`: `STATIC_PROVEN`.
- Separate `IDispatch::Invoke`-shaped callback attempt: `STATIC_PROVEN_CALLSITE`.
- Actual async/cyclic callback execution and HRESULT success: `UNKNOWN`.
- Exact per-request edge to this routine, `DISPPARAMS` semantics, and `pCB` versus `pDisp` retention: `UNKNOWN`.

## Evidence

- `corrections/dispatch/old_getdispids_objdump.txt`
- `corrections/dispatch/new_getdispids_objdump.txt`
- `corrections/dispatch/old_string_xrefs.txt`
- `corrections/dispatch/new_string_xrefs.txt`
- `/root/PL/stages/stage16_5/async_flow/old_dispatch_cleanup_disasm.txt`
- `/root/PL/stages/stage16_5/async_flow/new_dispatch_cleanup_disasm.txt`
