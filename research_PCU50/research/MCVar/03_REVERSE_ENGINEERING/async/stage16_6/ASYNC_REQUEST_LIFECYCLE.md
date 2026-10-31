# Static ReqID and Async Transaction Lifecycle

## Scope and evidence

Offline static analysis only, on the exact old/new `MCVar.dll` binaries listed below. No Windows executable, collector, live DDE, or callback runtime experiment was used. The staged Rizin disassembly in `../stage16_5/async_flow/{old_functions,new_functions}.txt` and the Rizin/Capstone boundary notes in `../stage16_5/async_flow/followup/readvar_async_boundary.md` supply the address-level evidence. Both files were refreshed/cross-checked against the binaries with Rizin in this stage. Raw lifecycle Rizin function dumps are in `raw/`.

- Old: `/root/PL/PCU_old/H/mmc2/MCVar.dll`, SHA-256 `43a5c1991d98b6b6e155233a0114d7ff72bf4dec7edf58d0607da501e7d98712`, image base `0x10000000`.
- New: `/root/PL/PCU_new/C/RECYCLER/S-1-5-21-4025392478-4199590385-3038547483-1005/Dc28/files/F/mmc2/MCVar.dll`, SHA-256 `5e7d955ebe7cfd52424b04e91471b7408f42bf6cc427e3d94c50bc7f4428c24a`, image base `0x10000000`.

The machine-readable field/edge ledger is [ASYNC_TRANSACTION_LAYOUT.json](ASYNC_TRANSACTION_LAYOUT.json).

## Corrected model: pointer, wrapper, value

Three distinct things must not be conflated:

1. **Caller `pReqID`** is a pointer supplied to `ReadVarAsync` for a request-ID output. `ReadVarAsync` passes it to the shared starter. The starter stores that pointer in the transaction record at `+0x98`. This is a pointer store, not a generated ID store.
2. **Generated/logged ReqID value** is a scalar used as `RID` in transaction logging and associated with a transaction field compared at `+0x20` by the starter. The available ReadVarAsync/starter slice does not identify the generator assignment sufficiently to claim its origin or sequence.
3. **12-byte result wrapper** allocated by `ReadVarAsync` is separate. Its `+0x04` holds the transaction/result pointer; `+0x08` is cleared. This wrapper field is not `pReqID`.

A later completion/result helper writes its computed result through a separate output pointer (`old 0x1000ff3e`, `new 0x10010050`). The static sequence supports a deferred caller-memory write, not the claim that `ReadVarAsync` itself writes the ID at entry.

## Lifecycle by edge

### 1. Request entry and allocation

Old `ReadVarAsync` is at `0x1000d28a`; new at `0x1000d39c`. Each directly calls the shared transaction starter (`old 0x1000d7a4` at callsite `0x1000d2d5`; `new 0x1000d8b6` at `0x1000d3e7`). In each starter, transaction construction/configuration culminates in a returned transaction pointer in `EAX` and `ret 0x38` (`old 0x1000d89a`; new equivalent `0x1000d9ac`). The ReadVarAsync body then allocates a 12-byte wrapper (`old 0x1000d2e0`, new `0x1000d3f2`), zeros `+0x04/+0x08`, installs its vtable/data pointer at `+0`, and saves it locally. Null allocation and null transaction lead to failure/cleanup branches.

Classification: entry-to-starter and wrapper allocation are direct, statically proven control/data-flow edges.

### 2. Caller pointer storage versus numeric value

In both starter bodies, the caller pointer is loaded from `[ebp+0x34]` and stored at transaction `[ebx+0x98]`:

- Old: `0x1000d819 mov eax,[ebp+0x34]`; `0x1000d842 mov [ebx+0x98],eax`.
- New: `0x1000d92b mov eax,[ebp+0x34]`; `0x1000d954 mov [ebx+0x98],eax`.

The starter separately compares a transaction field at `+0x20` and formats/logs `RID` in the `new CTransaction ... RID:0x%x` record. These support a distinct scalar ReqID/value path, but the instruction that generates/assigns that scalar is not recovered in the bounded ReadVarAsync slice. Do not infer that `+0x98` is an integer ReqID merely because it is associated with the request.

Classification: `pReqID` argument propagation/storage is direct proof. Generated value association is supported; generation source and full value flow remain unresolved.

### 3. Registration and lookup

The binaries expose named `CTransactionID` constructor, `StartTransaction`, `WaitComplete`, `Free`, `CloseUp`, `Delete`, destructor and `CList<CTransactionID>::DeleteAll` routines. The old/new names and addresses are recorded in the JSON ledger. The starter invokes a `new CTransaction` path and returns its transaction record. This proves lifecycle machinery exists and is relevant to the transaction implementation, but symbol names and vicinity alone do not prove exactly which registration/list insertion instruction is exercised for this ReadVarAsync call.

No direct instruction was established in the captured evidence that looks up this transaction by the generated ReqID scalar. Do not claim a ReqID-keyed map/list lookup, or equate `CTransactionID` naming with the generated scalar, until the actual compare/key use is decoded.

Classification: machinery presence and constructor/start call paths are proven; instance-specific registration linkage is unresolved at the captured boundary; ReqID-keyed lookup is not proven.

### 4. Result ownership and completion

On the return path, `ReadVarAsync` stores the transaction pointer at wrapper `+0x04`, then calls `fcn.10001ea1` (`old 0x1000d491`, new `0x1000d5a3`). The downstream completion/result helper includes a store through its output pointer (`old 0x1000ff3e`, new `0x10010050`), demonstrating a result/request-ID write outside the entry method.

Completion code has concrete indirect callsites. One completion/name-resolution path calls `IDispatch::GetIDsOfNames` at vtable slot `+0x14`; separately, a callback routine calls `IDispatch::Invoke`-shaped slot `+0x18` after a DISPID-like local is populated, with adjacent `OnDataChanged`/HRESULT diagnostics. These static paths establish name resolution and an invocation-shaped dispatch attempt, but the available slice does not bind a particular ReadVarAsync transaction to that callback routine or prove runtime success. A transaction-object vtable `+0x04` call is also present and remains semantically unresolved.

Classification: wrapper association and output write are direct data-flow evidence. The GetIDsOfNames and separate Invoke-shaped callsites are static evidence; ReadVarAsync-specific reachability, callback success, method packing, and execution thread/timing remain unresolved.

### 5. Cancellation, failure, and release

Old `fcn.1000cdfd` and new `fcn.1000cf0f` allocate a 12-byte object; on allocation success they set the status field at `+0x04` to `0x80004004`, call the initialization/helper at `+0x08`, clear `+0x08`, and return. The associated diagnostic is `Com-Object released or Async-Transaction cancelled`. This proves an error/cancellation-coded cleanup path, but not the full trigger-to-specific-transaction linkage or a universal cancellation behavior.

`CTransactionID::WaitComplete` branches on state and returns a `CResult`-related pointer or null; named `Free`, `CloseUp`, `Delete`, destructor and list deletion routines are present. These establish release/teardown facilities. Without the missing instance-specific registration/lookup edge, the exact point at which a ReadVarAsync transaction reaches each release routine is not fully closed.

Classification: cancellation/error object behavior and cleanup operations are directly visible; complete transaction-specific cancellation/release chain remains unresolved.

## Old/new comparison

Both binaries preserve the same 32-bit layout and key flow. New code is relocated: `ReadVarAsync` `+0x112`, starter `+0x112`; `+0x98` pointer storage, wrapper allocation and continuation roles match. Lifecycle symbol addresses differ, and the exact addresses are in the JSON. No semantic divergence in the evidenced pointer/value distinction was found.

## Edge classification summary

| Edge | Classification | Result |
|---|---|---|
| ReadVarAsync -> shared starter | Direct proven | Both binaries |
| Caller `pReqID` through args -> transaction `+0x98` | Direct proven | Stored pointer, not ID value |
| Starter-created transaction -> 12-byte wrapper `+0x04` | Direct proven | Distinct object/field |
| Generated scalar ReqID source | Value association, source unresolved | No claim of generator |
| Transaction registration/list linkage for this instance | Machinery proven, instance edge unresolved | No inference from names alone |
| Lookup keyed by ReqID scalar | Not proven | No lookup algorithm claimed |
| Completion output-pointer write | Direct proven | Deferred store observed |
| Indirect completion/callback callsites | Dispatch proven, callback meaning unresolved | No callback semantics promoted |
| Cancellation/error status and diagnostic | Direct proven | Trigger-to-instance binding incomplete |
| Wait/free/close/delete/destruct | Facilities proven, terminal binding incomplete | No exact per-request release sequence claimed |

## Remaining uncertainty

Closing the remaining edges requires decoding the exact `CTransactionID` constructor/StartTransaction call graph and all references to transaction `+0x20` and `+0x98`, followed through the relevant list operations and completion helper. This report does not convert symbol names, log labels, callback names, or vtable calls into stronger semantics than their bytes establish.
