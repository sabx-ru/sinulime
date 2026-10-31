# OnDataChanged callback dispatch reconstruction

## Scope and evidence standard

Static/offline only. The two inputs are PE32/i386 MCVar.dll files at image base `0x10000000`:

- Old: `/root/PL/PCU_old/H/mmc2/MCVar.dll`, timestamp 2004-06-23.
- New: `/root/PL/PCU_new/C/RECYCLER/S-1-5-21-4025392478-4199590385-3038547483-1005/Dc28/files/F/mmc2/MCVar.dll`, timestamp 2011-07-25.

No Windows executable, collector, DDE, or runtime COM test was used. Evidence consists of raw PE bytes disassembled with GNU objdump and call/function cross-checks with Rizin. Focused artifacts are in `corrections/dispatch/`.

## Result

In each build's read-callback routine, the code resolves the BSTR name `OnDataChanged` using an IDispatch-compatible slot `+0x14` (`GetIDsOfNames`), then issues a separate IDispatch-compatible slot `+0x18` call (`Invoke`). The output location supplied to the first call is passed as the DISPID argument to the second call. Thus lookup and invocation are distinct; `+0x14` is not callback delivery. The `+0x18` call is strong static evidence of an invocation attempt, not proof that a callback implementation was entered or succeeded.

## Old image

### Name resolution

The read-callback path begins at old `0x100145f1`. Exact call setup and call:

```asm
100145f1: 8d 85 30 ff ff ff    lea eax,[ebp-0xd0]
100145f7: 8d 55 ec             lea edx,[ebp-0x14]       ; output location
100145fa: bf 00 08 00 00       mov edi,0x800            ; LCID
100145ff: 89 45 d8             mov [ebp-0x28],eax       ; names-array element
10014602: 8b 43 14             mov eax,[ebx+0x14]       ; IDispatch-like object
10014605: 52                   push edx                 ; rgDispId = &[ebp-0x14]
10014606: 57                   push edi                  ; LCID = 0x800
10014607: 8d 55 b0             lea edx,[ebp-0x50]
1001460a: 6a 01                push 1                    ; cNames
1001460c: be c8 d6 02 10       mov esi,0x1002d6c8       ; RIID pointer storage
10014611: c7 45 e0 06 00 00 00 mov [ebp-0x20],6         ; prior setup within call frame
10014618: 8b 08                mov ecx,[eax]
1001461a: 52                   push edx                 ; rgszNames
1001461b: 56                   push esi                 ; riid
1001461c: 50                   push eax                 ; this
1001461d: ff 51 14             call dword ptr [ecx+0x14]
10014620: 85 c0                test eax,eax
```

The pointer at old `0x1002d6c8` refers to 16 zero bytes at the RIID argument location, i.e. `GUID_NULL`/`IID_NULL` storage; bytes afterward belong to adjacent data. This call establishes the slot and argument shape, not the semantic IID value as a non-null GUID. The `rgszNames` element is a stack BSTR address prepared earlier in this same function; at the simpler parallel conversion site the literal is directly assigned from `0x100320cc`, whose bytes decode UTF-16 `OnDataChanged`. The corresponding async/cyclic callback strings and logging behavior also identify this function family as callback dispatch. The input string for this call is constructed/copied into local storage; disassembly at `0x100145c2-0x100145f0` copies four DWORDs from the function's incoming stack parameters into locals, so the exact pointer provenance is caller-supplied and not directly a static string load at this specific site.

### Invocation

On successful lookup and after callback eligibility checks, old `0x1001468a-0x100146a3` issues the separate slot `+0x18` call:

```asm
1001468a: 33 c9                xor ecx,ecx
1001468c: 8b 43 14             mov eax,[ebx+0x14]       ; same interface object
1001468f: 51                   push ecx                 ; puArgErr = NULL
10014690: 51                   push ecx                 ; pExcepInfo = NULL
10014691: 51                   push ecx                 ; pVarResult = NULL
10014692: 8d 4d d8             lea ecx,[ebp-0x28]
10014695: 8b 10                mov edx,[eax]             ; vtable
10014697: 51                   push ecx                 ; DISPPARAMS*
10014698: 6a 01                push 1                    ; wFlags = 1
1001469a: 57                   push edi                 ; LCID = 0x800
1001469b: 56                   push esi                 ; riid pointer
1001469c: ff 75 ec             push [ebp-0x14]          ; DISPID output from lookup
1001469f: 50                   push eax                 ; this
100146a0: ff 52 18             call dword ptr [edx+0x18]
100146a3: 8b f8                mov edi,eax               ; returned HRESULT retained
```

With stdcall arguments pushed right-to-left, this matches the IDispatch::Invoke parameter layout: `this, dispIdMember, riid, lcid, flags, pDispParams, pVarResult, pExcepInfo, puArgErr`. Immediately afterward the code retains the returned HRESULT in `edi`, checks dispatch parameter/result state, and later reports a Dispatch callback HRESULT using the strings at `0x10033338` and `0x10033384`. This is independent evidence that the `+0x18` call is the delivery attempt.

The DISPPARAMS address is `[ebp-0x28]`; before lookup that local was set to the address `[ebp-0xd0]`, and earlier setup copies data into `[ebp-0xd0]`. Parameter variant types and exact SAFEARRAY/VARIANT shape need a separate full local-lifetime/typelib correlation; they are not inferred here.

## New image

The structure is equivalent with shifted addresses. Name resolution:

```asm
100146fb: 8d 85 30 ff ff ff    lea eax,[ebp-0xd0]
10014701: 8d 55 ec             lea edx,[ebp-0x14]
10014704: bf 00 08 00 00       mov edi,0x800            ; LCID
10014709: 89 45 d8             mov [ebp-0x28],eax
1001470c: 8b 43 14             mov eax,[ebx+0x14]
1001470f: 52                   push edx
10014710: 57                   push edi
10014711: 8d 55 b0             lea edx,[ebp-0x50]
10014714: 6a 01                push 1
10014716: be d8 e6 02 10       mov esi,0x1002e6d8       ; RIID pointer storage
1001471b: c7 45 e0 06 00 00 00 mov [ebp-0x20],6
10014722: 8b 08                mov ecx,[eax]
10014724: 52                   push edx
10014725: 56                   push esi
10014726: 50                   push eax
10014727: ff 51 14             call dword ptr [ecx+0x14]
1001472a: 85 c0                test eax,eax
```

New `0x1003311c` contains UTF-16 `OnDataChanged` used by the corresponding direct-name conversion path. As in old, this callback function builds/copies local name/argument data from inputs, and passes one name with LCID `0x800` and output pointer `[ebp-0x14]`. The numeric pointer at `0x1002e6d8` is passed as RIID; the GUID value is not asserted here.

Invocation at new `0x10014794-0x100147ad`:

```asm
10014794: 33 c9                xor ecx,ecx
10014796: 8b 43 14             mov eax,[ebx+0x14]
10014799: 51                   push ecx                 ; puArgErr = NULL
1001479a: 51                   push ecx                 ; pExcepInfo = NULL
1001479b: 51                   push ecx                 ; pVarResult = NULL
1001479c: 8d 4d d8             lea ecx,[ebp-0x28]
1001479f: 8b 10                mov edx,[eax]
100147a1: 51                   push ecx                 ; DISPPARAMS*
100147a2: 6a 01                push 1                    ; wFlags
100147a4: 57                   push edi                 ; LCID = 0x800
100147a5: 56                   push esi                 ; riid pointer
100147a6: ff 75 ec             push [ebp-0x14]          ; resolved identifier
100147a9: 50                   push eax                 ; this
100147aa: ff 52 18             call dword ptr [edx+0x18]
100147ad: 8b f8                mov edi,eax
```

The same `DISPID` output location from lookup is consumed at Invoke argument position. The call then records and checks the returned HRESULT. New diagnostic strings are at `0x10034380` (returned HRESULT) and `0x100343cc` (called).

## Independent verification: lookup versus Invoke

- IDispatch vtable order places `GetIDsOfNames` at zero-based slot 5 (`+0x14`) and `Invoke` at slot 6 (`+0x18`); the argument lists at these callsites independently match those respective signatures.
- The `+0x14` output address is `[ebp-0x14]`. The later `+0x18` call pushes the dword at `[ebp-0x14]` in the DISPID position, proving dataflow from lookup to invocation.
- Both calls use the same object pointer loaded from `[ebx+0x14]` and its vtable from `[eax]`.
- The `ChangeArrayType` sites old `0x1000fef1` and new `0x10010003` are likewise `+0x14` name lookup, but that separate path continues to `ExecuteAsync` and must not be called callback delivery.
- No direct callback-interface virtual method call is established by these particular sites; the observed delivery path is late-bound IDispatch Invoke.

## Unresolved edge

The static evidence reaches the exact `Invoke` boundary and shows its HRESULT retained and checked. It does not identify the runtime object's concrete class, prove that its `Invoke` vtable entry resolves successfully, show a successful HRESULT, or prove user callback code executed. The RIID bytes are not decoded into a semantic GUID in this note; no identity is guessed. The input name's exact allocation/source and every DISPPARAMS variant's semantic type remain open. The raw LCID `0x800` is intentionally reported literally.

## Preserved artifacts

- `corrections/dispatch/old_context.txt`, `new_context.txt`
- `corrections/dispatch/old_10014500.txt`, `new_10014700.txt`
- `corrections/dispatch/old_getdispids_objdump.txt`, `new_getdispids_objdump.txt`
- Original DLLs listed above
