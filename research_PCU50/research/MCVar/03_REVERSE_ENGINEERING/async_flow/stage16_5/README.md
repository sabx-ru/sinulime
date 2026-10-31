# ReadVarAsync static reverse engineering evidence

Scope: offline static analysis of the exact MCVar.dll inputs supplied for stage 16.5. No source archives, Windows tools, or live DDE activity were used. Commands were run with Rizin `aaa`, `afl`, `pdf`, `px`, and `axt`.

## Inputs

- Old: `/root/PL/PCU_old/H/mmc2/MCVar.dll`, SHA-256 `43a5c1991d98b6b6e155233a0114d7ff72bf4dec7edf58d0607da501e7d98712`, PE32 i386, image base `0x10000000`, built 2004-06-23.
- New: `/root/PL/PCU_new/C/RECYCLER/S-1-5-21-4025392478-4199590385-3038547483-1005/Dc28/files/F/mmc2/MCVar.dll`, SHA-256 `5e7d955ebe7cfd52424b04e91471b7408f42bf6cc427e3d94c50bc7f4428c24a`, PE32 i386, image base `0x10000000`, built 2011-07-25.

## Concrete implementation

The public COM method is the 690-byte dual-interface implementation:

| binary | VA | RVA | raw entry bytes | direct result |
|---|---:|---:|---|---|
| old | `0x1000d28a` | `0xd28a` | `85 c0 59 74 4f 8b 4d f0 8b d3 c1 e2 04 f7 d9 8d 94 15 88 b1 ff ff 8d 75 b4 1b c9 23 ca 51` | `CVar2::ReadVarAsync(VARIANT,VARIANT,VARIANT,short,IReadVarAsyncCallback2*,IDispatch*,long*,VARIANT*)`, Rizin size 690 |
| new | `0x1000d39c` | `0xd39c` | `85 c0 59 74 4f 8b 4d f0 8b d3 c1 e2 04 f7 d9 8d 94 15 88 b1 ff ff 8d 75 b4 1b c9 23 ca 51` | same signature, Rizin size 690 |

The old/new entry bytes are identical; the function is relocated by `+0x112` RVA in new. The legacy `IReadVarAsyncCallback*` overload is an 18-byte forwarding thunk at old `0x1000d3f6` (RVA `0xd3f6`) and new `0x1000d508` (RVA `0xd508`), with identical first bytes `00 a8 01 0f 84 8b 00 00 00 83 7d f8 01 b8 ...`; Rizin labels its body as part of the main flow due to overlap/analysis ambiguity. Treat the 690-byte dual entry as the implementation entry and the short overload as a wrapper/continuation, not an independent implementation.

## Proven control flow in the implementation

At old `0x1000d28a` / new `0x1000d39c`:

1. A nonzero object/result from the preceding command-building path is tested; the main path calls the internal transaction starter at old `0x1000d7a4` / new `0x1000d8b6`.
2. A 12-byte transaction/result object is allocated through old `0x10017dd5` / new `0x10017ee5`; its first fields are zeroed and a vtable/data pointer is installed. Null allocation or null transaction goes to the terminal cleanup/error path.
3. Callback/interface capability is read through `fcn.100017f3`, with vtable slot checks (`mov eax,[eax+0xc]; mov eax,[eax]; test al,1`). The dual callback path checks both callback-related objects before dispatch; the legacy path checks the callback interface and conditionally reaches the same start logic. The explicit validation string `Wrong callback interface pointer` is referenced from the command-building/validation function at old `0x1000c952` and new `0x1000ca64`, not from the ReadVarAsync body itself.
4. Request setup selects `Master` or `Slave` based on a mode value and calls a common trace/log helper at old `0x10009daf` / new `0x10009ec1`. The ReadVar branch directly references `StartRead` format at old `0x1000d47d` / new `0x1000d58f`, including `RID`, name, cache, server handle, and client handle. The alternate branches reference `StartWrite` and `StartExec`; these are shared transaction machinery, not proof that ReadVarAsync performs write/execute operations for a read request.
5. After start, the transaction pointer is stored at `[transaction+4]`; `fcn.10001ea1` is called (old and new same VA/RVA) to obtain/prepare a result. The returned BSTR length is read via `SysStringLen`; optional result variants use `VariantCopy`.
6. Client-handle validation is concrete: `IsBadReadPtr(...,4)` then comparison against magic `0x890abcde`; valid handle value is copied, invalid is zeroed. The loop increments an index and repeats until the variable count, then enters the internal transaction path or cleanup.

The exact disassembly excerpts are in `old_functions.txt`, `new_functions.txt`, `old_calls.txt`, and `new_calls.txt`; raw bytes are in `old_bytes.txt` and `new_bytes.txt`.

## Completion/callback path evidence

The implementation itself does not contain a direct call to a user callback method by symbolic name. Static evidence establishes the callback contract and downstream dispatch helpers:

- Typelib/resource strings include `ReadVarAsync`, `IReadVarAsyncCallback2WW`, `IReadVarAsyncCallbackWWWX`, and `OnCommandCompleted` in both images.
- `OnCommandCompleted` is referenced by old `CVar2::MakeCommandString` at `0x1000ca12` and `CXVariant::Append` at `0x100148b3`; new equivalents are `0x1000cb24` and `0x100149bd`.
- `OnDataChanged` and `OnWriteComplete` are referenced by the common completion/dispatch routine old `fcn.100138b8` (`0x100138e6`, `0x100138ef`) and new `fcn.100139c2` (`0x100139f0`, `0x100139f9`). These are concrete callback-name construction/dispatch-path references; old `fcn.1000fc68` and new `0x1000fffc` also reference `OnDataChanged` in adjacent completion logic.
- The cancellation/error diagnostic `Com-Object released or Async-Transaction cancelled` is referenced by old `fcn.1000cdfd` at `0x1000ce0c`, new `fcn.1000cf0f` at `0x1000cf1e`. This is concrete cleanup/error handling, but the exact HRESULT mapping requires further function-level annotation.
- `new CTransactionID` is referenced by old `fcn.1000cf94` at `0x1000d021`, new `fcn.1000d0a6` at `0x1000d133`; `StartRead` is referenced by old `fcn.1000d1bd` at `0x1000d776`, new `fcn.1000d2cf` at `0x1000d888`. These callees are the transaction allocation/start and downstream read-start machinery.

## Confidence and unresolved edges

- **High confidence:** concrete entry VA/RVA, exact signature labels, 690-byte implementation size, old/new relocation, entry bytes, transaction allocation, request setup/logging, result/variant handling, handle validation, and cleanup diagnostic xrefs.
- **Medium confidence:** `fcn.1000d7a4`/`0x1000d8b6` is the internal transaction starter for ReadVarAsync, because the call is direct and occurs before transaction object setup, but its full semantic contract is shared with write/execute branches.
- **Medium confidence:** callback dispatch is routed through the completion helpers containing `OnCommandCompleted`/`OnDataChanged`/`OnWriteComplete`; direct proof of the final indirect vtable slot invoked for `ReadVarAsync` is not present in the captured entry disassembly. The callback interface method ordinal and exact argument packing remain unresolved.
- **Unresolved edge:** the full terminal path after the per-variable loop, including exact `CTransactionID::WaitComplete`/`CloseUp` interaction and whether callback release happens synchronously or from a message/worker callback, needs a dedicated follow-up over `fcn.1000d776`/`0x1000d888`, `CTransactionID` destructor/close paths, and the completion helper. This report intentionally does not broaden into general DDE tracing.
