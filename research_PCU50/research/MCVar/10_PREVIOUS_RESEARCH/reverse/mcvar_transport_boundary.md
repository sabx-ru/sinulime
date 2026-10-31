# Track A: MCVar request-object call and smallest transport boundary

## Scope

Offline static analysis of the preserved old image `/root/PL/PCU_old/H/mmc2/MCVar.dll`. No vendor execution, live endpoint, hash, or runtime object capture was used. `PCU_old`, `PCU_new`, and `real_tests` inputs were not modified.

## Finding at `0x10004E2E`

The exact bytes and surrounding instructions are preserved in:

- `mcvar_4ca7_4e40_raw.asm`
- `mcvar_10004e2e.asm`
- `reviewer_track_a_boundary.asm`

The relevant sequence is:

```asm
10004DD1  mov  ecx,[esi+14h]
10004DD4  lea  eax,[esi+24h]
10004DD7  lea  ebx,[esi+18h]
10004DDA  push esi
10004DDB  push eax
10004DDC  push ebx
10004DDD  call 10001AF5          ; produces CResult* in EAX
10004DE2  test eax,eax
10004DE4  mov  [ebp-4],eax       ; result object
...
10004E22  mov  eax,[ebp-4]
10004E25  mov  edx,[esi]          ; EDX = receiver vptr
10004E27  push 0
10004E29  mov  ecx,esi            ; this = same receiver
10004E2B  mov  eax,[eax]          ; first argument = *(CResult*)
10004E2D  push eax
10004E2E  call dword ptr [edx+4]
```

Thus this is a `thiscall` virtual call on `ESI`, with arguments `(result_value, 0)`. `EDX` is not an independently created request object: it is exactly the vptr loaded from the receiver at `[ESI]`.

## Vptr and slot resolution

The surrounding function is the `CDdeAction::StartPoke`/`CXVariant::GetNcddeBinaryData` overlapping symbol region, and `ESI` is the active local object used by the conversion/result path. The relevant vtable prefix is recovered from `.rdata`:

```text
vtable 0x1002C3A0:
  +0x00 -> 0x100010D3
  +0x04 -> 0x100010D6
  +0x08 -> 0x10007B8A
```

The `+4` target is therefore `0x100010D6`, whose exact body is only `ret 4`. This is a no-op result/variant virtual slot, not a DDE API, IPC bridge, `StartRequest`, `DdeClientTransaction`, or `DdeCreateDataHandle` edge. The same vtable prefix pattern occurs in neighboring `CXVariant`-family tables; `0x10007B8A` is a later slot and is not called by `0x10004E2E`.

Vptr installation evidence includes `0x10007B91: mov [esi],0x1002C3A0` and `0x10002F01: mov [esi],0x1002C3A0`. The call site therefore resolves to a local virtual result operation when this vtable variant is active. Other nearby conversion branches use the same `[vptr+4]` idiom with their own class table, but none of the resolved slot targets constitutes transport.

## Relation to request flow

`0x10004CA7` is a dispatcher/conversion routine. Its `0x10004DD1` branch calls `0x10001AF5`, stores the returned `CResult*`, and then performs the `0x10004E2E` result operation. Other branches at `0x10004EEC`, `0x10004F22`, and `0x10004F53` repeat the pattern: obtain a result object, call `[ESI-vptr+4]`, then call `0x10004CA7` again with `0x10`.

This is not the MCVar request submission boundary. The direct MCVar read construction edge remains:

```text
CVar2::ReadVar body 0x1000BC30
  -> request/conversion helper 0x1000C532 at 0x1000BD47
  -> unresolved downstream request/transport operation
```

`0x1000BDDC -> 0x10014CBE` remains cleanup/lifetime handling. `0x10014CBE` calls an attached object’s vtable slot `+8`; it is not submission. No direct `ReadVar -> CDdeAction::StartRequest` call or concrete MCVar-to-ncdde cross-module edge was recovered.

## Smallest exact boundary

The smallest exact boundary established by this pass is **not** `0x10004E2E -> transport`; it is the local result-dispatch boundary:

```text
result-producing conversion at 0x10001AF5
  -> CResult* saved at [EBP-4]
  -> receiver vptr [ESI]
  -> virtual slot +4 at 0x10004E2E
  -> 0x100010D6 (ret 4 for vtable 0x1002C3A0)
```

The smallest exact MCVar-side request boundary that remains actionable is `ReadVar 0x1000BD47 -> 0x1000C532`. The transport API/message edge beyond `0x1000C532` is unresolved. Existing ncdde evidence independently proves request handling and `DdeCreateDataHandle` writers, but no static object/data-flow join to this MCVar path is established. Therefore this report does not claim DDE for `0x10004E2E`.
