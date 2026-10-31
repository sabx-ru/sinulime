# ReadVarAsync next async causal boundary

Scope: offline static analysis only. Exact old/new `MCVar.dll` inputs; no source archive edits, Windows tools, or DDE activity. Independent Capstone/pefile byte decoding plus Rizin disassembly cross-check.

Inputs:

- Old `/root/PL/PCU_old/H/mmc2/MCVar.dll`, SHA-256 `43a5c1991d98b6b6e155233a0114d7ff72bf4dec7edf58d0607da501e7d98712`, image base `0x10000000`.
- New `/root/PL/PCU_new/C/RECYCLER/S-1-5-21-4025392478-4199590385-3038547483-1005/Dc28/files/F/mmc2/MCVar.dll`, SHA-256 `5e7d955ebe7cfd52424b04e91471b7408f42bf6cc427e3d94c50bc7f4428c24a`, image base `0x10000000`.

## Resolved causal boundary

`ReadVarAsync` does not write the caller's `pReqID` itself. It passes the caller pointer through the shared transaction starter, which stores it in the newly allocated transaction record; the downstream completion/result path writes the generated ID through that stored pointer.

### Old bytes / instructions

At `ReadVarAsync` old `0x1000d28a`, the starter call is direct:

```text
1000d2d5: e8 ca 04 00 00       call 1000d7a4
```

At old starter `0x1000d7a4`, the transaction record receives the request-ID pointer in its `+0x98` field:

```text
1000d819: 8b 45 34             mov eax, dword ptr [ebp+0x34]
1000d842: 89 83 98 00 00 00    mov dword ptr [ebx+0x98], eax
```

The starter is a `ret 0x38` function and returns the transaction pointer in `EAX` (`1000d894: 8b c3; ... 1000d89a: c2 38 00`). The ReadVarAsync continuation stores that transaction/result object and calls the result-preparation helper:

```text
1000d48d: 8b 4d 28             mov ecx, dword ptr [ebp+0x28]
1000d490: 50                   push eax
1000d491: 89 48 04             mov dword ptr [eax+4], ecx
1000d494: e8 08 47 ff ff       call 10001ea1
```

The downstream completion/result routine contains the actual caller-pointer write. Its concrete sequence is:

```text
1000ff28: 33 c0                xor eax, eax
1000ff2a: 3b c3                cmp eax, ebx
1000ff2c: 89 45 f4             mov dword ptr [ebp-0xc], eax
1000ff2f: 75 0a                jne 1000ff3b
1000ff31: e8 3d 1f ff ff       call 10001e73
1000ff3b: 8b 4d 2c             mov ecx, dword ptr [ebp+0x2c]
1000ff3e: 89 01                mov dword ptr [ecx], eax
```

The `arg_2c` pointer is the result/request-ID output pointer for this completion helper. This is the first concrete store of the generated result into caller memory found after the ReadVarAsync entry; the entry itself has no `mov [arg_*], ...` request-ID store.

### New bytes / instructions

The old/new implementation is relocated but structurally equivalent. New starter call:

```text
1000d3e7: e8 ca 04 00 00       call 1000d8b6
```

New starter record field:

```text
1000d92b: 8b 45 34             mov eax, dword ptr [ebp+0x34]
1000d954: 89 83 98 00 00 00    mov dword ptr [ebx+0x98], eax
```

New ReadVarAsync continuation:

```text
1000d59f: 8b 4d 28             mov ecx, dword ptr [ebp+0x28]
1000d5a2: 50                   push eax
1000d5a3: 89 48 04             mov dword ptr [eax+4], ecx
1000d5a6: e8 fa 45 ff ff       call 10001ea1
```

New completion/result write:

```text
1001003a: 33 c0                xor eax, eax
1001003c: 3b c3                cmp eax, ebx
1001003e: 89 45 f4             mov dword ptr [ebp-0xc], eax
10010041: 75 0a                jne 1001004d
1001004d: 8b 4d 2c             mov ecx, dword ptr [ebp+0x2c]
10010050: 89 01                mov dword ptr [ecx], eax
```

## Completion/callback dispatch evidence

The common completion helper is old `fcn.1000fc68` / new `fcn.1000fd7a`. After callback/interface validation, it performs an actual indirect interface call at vtable slot `+0x14`:

Old:

```text
1000fed3: 8b 07                mov eax, dword ptr [edi]
1000fee9: 57                   push edi
1000fef1: ff 50 14             call dword ptr [eax+0x14]
1000feea: c7 45 10 cc 20 03 10 mov dword ptr [ebp+0x10], 100320cc
```

`0x100320cc` is the UTF-16 `OnDataChanged` name. This is a concrete callback/dispatch call, with `EDI` as the validated callback interface and slot `+0x14` (20 decimal). The same bytes/role in new are:

```text
1000ffe5: 8b 07                mov eax, dword ptr [edi]
1000fffc: c7 45 10 1c 31 03 10 mov dword ptr [ebp+0x10], 1003311c
10010003: ff 50 14             call dword ptr [eax+0x14]
```

The transaction completion routine also has a separate indirect call through the transaction object's vtable slot `+0x04`:

Old:

```text
10010220: 8b 16                mov edx, dword ptr [esi]
10010229: ff 52 04             call dword ptr [edx+0x04]
```

New equivalent:

```text
10010222: 8b 16                mov edx, dword ptr [esi]
10010229: ff 52 04             call dword ptr [edx+0x04]
```

This call is reached after checking the transaction/callback object and magic `0x890abcde`; it is the strongest direct completion callback dispatch candidate. The object vtable at `ESI` is not statically tied uniquely to the `ReadVarAsync` callback interface in the available slice. Therefore the callback method ordinal/argument packing and whether this is the final worker/message callback remain unresolved.

## Exact unresolved boundary

Resolved:

1. `ReadVarAsync` -> shared starter (`old 0x1000d7a4`, new `0x1000d8b6`).
2. Starter creates/configures the transaction record and stores caller `pReqID` at transaction `+0x98`.
3. Completion/result helper writes the generated request ID through its output pointer (`old 0x1000ff3e`, new `0x10010050`).
4. Completion code has concrete indirect dispatch: callback interface slot `+0x14` for `OnDataChanged`, and transaction-object slot `+0x04` in the terminal completion branch.

Unresolved exactly: the edge between the transaction record's async completion/event owner and the `ReadVarAsync` callback object's final method invocation. Static bytes establish the two indirect calls above, but do not prove which one is the callback method for this specific ReadVarAsync transaction, nor establish synchronous versus worker/message-thread timing. No callback behavior is inferred.
