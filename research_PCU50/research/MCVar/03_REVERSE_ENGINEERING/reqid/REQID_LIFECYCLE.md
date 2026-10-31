# ReqID Lifecycle: Static Dataflow

## Scope and inputs

Offline static analysis of exact 32-bit `MCVar.dll` old/new binaries only. No Windows execution, DDE, source archive modification, or runtime test was used.

- Old: `/root/PL/PCU_old/H/mmc2/MCVar.dll`, SHA-256 `43a5c1991d98b6b6e155233a0114d7ff72bf4dec7edf58d0607da501e7d98712`, image base `0x10000000`.
- New: `/root/PL/PCU_new/C/RECYCLER/S-1-5-21-4025392478-4199590385-3038547483-1005/Dc28/files/F/mmc2/MCVar.dll`, SHA-256 `5e7d955ebe7cfd52424b04e91471b7408f42bf6cc427e3d94c50bc7f4428c24a`, image base `0x10000000`.

Instructions below were inspected with Rizin against the binaries. `stage16_6/async/ASYNC_REQUEST_LIFECYCLE.md` and `ASYNC_TRANSACTION_LAYOUT.json` supplied previously established entry-to-starter and wrapper edges. The exact `ReadVarAsync` vtable targets are now corroborated by direct method pointers/call edges, and constructor/StartTransaction bodies plus direct call xrefs were captured separately; see `evidence/*reqid*raw.txt` and `evidence/*reqid_direct_xrefs.txt`.

## Keep the identities separate

1. **Caller output pointer (`pReqID`)**: `ReadVarAsync` passes this pointer through the starter arguments. In the starter it is loaded from `[ebp+0x34]` and stored in transaction-record `[ebx+0x98]` (old `0x1000d819`, `0x1000d842`; new `0x1000d92b`, `0x1000d954`). That is pointer dataflow, not an integer ReqID assignment.
2. **Transaction pointer**: the starter returns a `CTransaction` record pointer in `EAX`; `ReadVarAsync` separately stores that pointer in its 12-byte result wrapper at `+0x04` (old `0x1000d48d-0x1000d494`; new `0x1000d59f-0x1000d5a6`). Neither is the caller output pointer.
3. **Numeric transaction/request identifier**: the starter reads transaction `[+0x20]`, tests it, and passes a scalar to the `new CTransaction ... RID:0x%x` formatter (old starter `0x1000d858-0x1000d88c`; corresponding new code is at `+0x112`). This establishes a scalar/log association. The inspected slice does not recover its producer or prove that this scalar is the value ultimately written to `pReqID`.
4. **Cyclic ID**: cyclic methods have their own `CCyclicID` object/list and logs explicitly named `CCyclicID/ReqID`. Do not equate that object or its field with the `CTransactionID` lifecycle or the async transaction record.

## Lifecycle findings

### Creation and entry

Old `ReadVarAsync` (`0x1000d28a`) has an exact direct call at `0x1000d2d5` to shared starter `0x1000d7a4`; new entry/starter are `0x1000d39c`/`0x1000d8b6`, call at `0x1000d3e7`. These are actual implementations, not inferred from label-only metadata. Starter return is a transaction-record pointer (`EAX`), and it initializes/configures the record (`ret 0x38`). `+0x98` receives the caller pointer. Constructor/list lifecycle remains separate unless a direct constructor or insertion edge joins it.

The constructor (`old 0x1000df94`, new `0x1000e0a6`) takes `CList<CTransactionID*>*` and `CVar2*`; its implementation body performs extensive setup and includes the `new CTransactionID ... lst:... var2:...` diagnostic. `CRequestID` is a different constructor (`old 0x1000e044`, new `0x1000e156`); its body parses/validates data, and direct xrefs do not join it to the async entry/starter. `StartTransaction` is separately located (`old 0x1000e1bd`, new `0x1000e2cf`), but its function range overlaps the destructor's apparent decoded body, so its apparent 7-byte boundary is unreliable. Preserve raw bytes/disassembly as evidence, not trust the label boundary. No direct call from the async starter into either constructor or `StartTransaction` was found in the disassembled cross-reference output.

The presence of constructor/list setup and `StartTransaction` machinery is real, but does not alone prove that this `ReadVarAsync` request creates or inserts a transaction-ID object.

### Registration and lookup

The binary contains `CTransactionID::WaitComplete`, `Free`, `CloseUp`, `Delete`, destructor, and `CList<CTransactionID*>::DeleteAll` routines. Symbol/function presence proves lifecycle machinery, not a per-ReadVarAsync path. The evidence inspected here does not close a direct call chain from the async starter to a specific list insertion, nor identify the list key comparison used to find that object.

Accordingly, **ReqID-keyed lookup is not established**. In particular, the `+0x20` scalar test and RID log argument do not show that a lookup compares a caller-provided scalar against `+0x20`; likewise, `+0x98` cannot be interpreted as an ID key because actual instructions store the caller pointer there.

### Completion and cleanup

The stage16.6 evidence identifies a downstream completion/result helper that writes through its output pointer (old `0x1000ff3e`, new `0x10010050`), distinct from starter storage at `+0x98`. Static evidence therefore supports a deferred output write, but not the exact numeric producer-to-output identity without connecting the helper argument back to this request.

The cancellation/error helper sets status `0x80004004` and has the diagnostic “Com-Object released or Async-Transaction cancelled” (old `0x1000cdfd-0x1000ce23`, new `0x1000cf0f-0x1000cf35`). `WaitComplete` and the cleanup methods exist. The exact request-to-cancel/wait/free/delete/destructor path remains open because instance registration/lookup was not demonstrated.

`CCyclicID` is separate: its constructor is old `0x100113ba`; `CVar2::StartCyclics`, `CCyclicID::Delete`, and `CList<CCyclicID*>::DeleteAll` are distinct routines. Its strings “new/free CCyclicID/ReqID” and cyclic read/remove ReqID logs do not bridge it to `CTransactionID`.

## Old/new comparison and confidence

Old/new async entry, starter, pointer store, wrapper, and completion-helper addresses show the previously observed `+0x112` relocation for the matched code. The exact lifecycle symbol addresses are in `REQID_DATAFLOW.json`. No change in pointer/value separation is indicated. Constructor and cleanup names are treated as labels; claims about exact registration, key comparison, or terminal per-request linkage remain unresolved.

## Evidence classifications

- **Direct instruction proof**: caller pointer stored at transaction `+0x98`; starter return is a transaction pointer; wrapper `+0x04` holds that pointer; starter tests `+0x20` and supplies a scalar to RID formatting; distinct cyclic object/list routines exist.
- **Machinery present, request linkage unresolved**: `CTransactionID` list constructor, wait/free/close/delete/destructor, list `DeleteAll`.
- **Not proven**: the numeric ID generator, whether the completion output value is that exact scalar, specific async list insertion, ReqID-keyed lookup/comparison, and exact per-request cancel/wait/release sequence.

The machine-readable evidence ledger is [REQID_DATAFLOW.json](REQID_DATAFLOW.json); known object fields and limitations are in [ASYNC_OBJECT_LAYOUT.json](ASYNC_OBJECT_LAYOUT.json).
