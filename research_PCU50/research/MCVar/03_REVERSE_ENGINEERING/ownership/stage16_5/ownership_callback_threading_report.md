# MCVar async/cyclic ownership and threading evidence

Scope: static, offline analysis of the two supplied PE32 `MCVar.dll` images. No archive or binary was modified. Addresses below are image VAs from each binary's preferred base (`0x10000000`). Raw captures: `old_import_xrefs.txt`, `new_import_xrefs.txt`, `old_raw_function_evidence.txt`, and `new_raw_function_evidence.txt` in this directory. Existing string inventories are in `../evidence/rizin_old_async_cyclic_strings.txt` and `../evidence/rizin_new_async_cyclic_strings.txt`.

Binary identity:

- Old: compiled 2004-06-23; size `0x6a251`; SHA-256 `43a5c1991d98b6b6e155233a0114d7ff72bf4dec7edf58d0607da501e7d98712`.
- New: compiled 2011-07-25; size `0x6b389`; SHA-256 `5e7d955ebe7cfd52424b04e91471b7408f42bf6cc427e3d94c50bc7f4428c24a`.

## Direct evidence

### COM ownership and interface dispatch

Both images import ATL `AtlInternalQueryInterface` and `AtlComPtrAssign`. Xrefs show `AtlInternalQueryInterface` used by the `CVar2::FinalConstruct`/class-factory-related paths and ATL cached class-factory methods. This is direct evidence that ATL supplies interface-map QI mechanics for at least the exposed COM objects; it does not prove every callback pointer is retained by `AddRef`.

Both images import `InterlockedIncrement` and `InterlockedDecrement`. `InterlockedDecrement` is referenced by the ATL/object teardown and several internal helper regions. This supports atomic reference-count/lifetime operations, but the stripped/disassembler view does not safely assign every decrement to `CVar2`, request, or callback ownership. No standalone `AddRef`/`Release` semantic proof was recovered for the async request records.

`AtlComPtrAssign` is direct evidence of ATL smart-pointer assignment in error/result paths. It is consistent with COM pointer ownership, but is not proof that the async callback is held in a smart pointer rather than a raw field.

### Async callback surface and callback storage clues

The embedded type/resource names identify `IMCCommandAsyncCallback`, `IReadVarAsyncCallback2`, `IWriteVarAsyncCallback2`, `IReadVarAsyncCallback`, `IWriteVarAsyncCallback`, and `DIMCCommandAsyncCallback`; exported/type-library-like resource names also contain `ReadVarAsync`, `WriteVarAsync`, and `ExecuteAsync`.

The `CVar2` method signatures recovered by Rizin include:

- `ExecuteAsync(VARIANT, long, IMCCommandAsyncCallback *, IDispatch *, long *)`.
- `WriteVarAsync(..., IWriteVarAsyncCallback *, IDispatch *, long *, VARIANT *)`.

The corresponding `ReadVarAsync` strings and method resources are present for both `IVar` and `IVar2`. These are direct interface/call-surface facts.

The async error helper is nearly identical in both images: old `fcn.1000cdfd`, new `fcn.1000cf0f`. It allocates/obtains a 12-byte record through `fcn.10017dd5` (old) / `fcn.10017ee5` (new), tests the result, writes `0x80004004` (`E_ABORT`) at record offset `+0`, writes error text through the helper called with `record+4`, clears record offset `+8`, and returns the record. The literal is `Com-Object released or Async-Transaction cancelled`. Directly established: a cancellation/release result record has at least status, message/result payload at `+4`, and a field at `+8` cleared during this path. The meaning of `+8` and who frees the record remain unresolved.

Both images contain the literal `Callback pointers not checked` near the callback dispatch code. This is direct evidence of an explicit unchecked-pointer condition/logging statement, not evidence that callbacks are safe or reference-counted.

### Callback dispatch

Both images contain `OnDataChanged` and eight diagnostic strings distinguishing `Dispatch` and `Dual` callback invocation for `IVar2` and `IVar`. The diagnostics record request ID, callback/object address, HRESULT, and whether the call was made. Directly established: dispatch has at least two paths, late-bound `IDispatch` and a dual/vtable-style path, and HRESULTs are observed after the call.

This is callback dispatch evidence, not proof of COM apartment marshaling. The imports do not include `CoMarshalInterface`, `CoUnmarshalInterface`, `CoMarshalInterThreadInterfaceInStream`, or `CoGetInterfaceAndReleaseStream` in either image. Therefore cross-apartment callback behavior is unresolved; do not model it as automatic marshaling.

### Cyclic/request objects and layout clues

Both string inventories directly record:

- `CCyclic::Init`.
- `new CCyclicID/ReqID ... var2:...` and `free CCyclicID/ReqID`.
- `StartCyclic ... RID ... crit ... shdl ... chdl ... rupd` and `new Cyclic ... RID ... crit ... shdl ... dead ... rupd`.
- `free CCyclic`.
- `ReadVarCyclic`, `RemoveCyclicVariables`, `DataChange`, `IdleCB`, and `FlushCyclics`.

The cyclic flush disassembly gives stronger layout clues. Old `fcn.10011d7f` starts with `this` in `ESI`, reads the linked-list head at `[this+0x0c]`, follows each node's next pointer at `[node+0]`, and obtains a cyclic object at `[node+0x08]`. It reads cyclic state/flags at `[cyclic+0x80]`, a mode/state at `[cyclic+0x74]`, and selects data at `[cyclic+0x38]` or `[cyclic+0x40]` based on a flag. New `fcn.10011d5f`/`InternalRemoveCyclicVariables` uses the corresponding shifted layout clues: `this` fields include `[this+0x0c]`, and cyclic fields include `[cyclic+0x38]`, `[cyclic+0x40]`, `[cyclic+0x5e]`, `[cyclic+0x74]`, `[cyclic+0x80]`, `[cyclic+0x84]`, and `[cyclic+0x88]`. The new image's direct `CCyclic::Data` method xrefs also enter/leave a critical section.

These offsets are direct memory accesses, but field names and complete struct sizes are inference. The node's `+0x08` is best described as a cyclic-object pointer because the code immediately dereferences cyclic fields; the node's `+0` is a next-link because it controls iteration. No claim is made that this is a C++ standard-layout struct or that offsets are stable across builds.

### Locks, timers, and thread/message evidence

Both images import and reference `InitializeCriticalSection`, `EnterCriticalSection`, `LeaveCriticalSection`, and `DeleteCriticalSection` in the same object-management/helper clusters. This directly establishes critical-section-based synchronization and cleanup. New `CCyclic::Data` has direct enter/leave xrefs. The exact lock field and lock ordering are unresolved.

Both images import `CreateMutexA`, `WaitForSingleObject`, `Sleep`, TLS functions, and `GetCurrentThreadId`; xrefs for mutex/wait/TLS were not assigned confidently to the cyclic records in this pass. Treat them as module-level concurrency facilities, not proof of a specific async object's worker thread.

Both images import `SetTimer`, `KillTimer`, `GetMessageA`, `PostMessageA`, and `DispatchMessageA`. Direct xrefs show timer setup/teardown in old `fcn.1000287c`/`g_trace...` and new `fcn.100028bb`/`g_trace...`, plus another `SetTimer` site old `fcn.100058d3`, new `fcn.10005912`. The strings `TimerCallback ... server ... cooky` and `TimerCallback ... RecursionLock` are present in both. This establishes timer/callback and recursion-lock instrumentation, but does not prove the cyclic object itself owns the timer or that callbacks run on a dedicated thread.

Neither import table exposes `CreateThread` in the recovered list. Do not infer a worker thread solely from `Sleep`, waits, TLS, or timers; the timer/message loop may be UI-thread driven or delegated through another component.

## Inferences and confidence

- **High confidence:** ATL-backed COM interface-map/QI machinery is used; atomic refcount primitives exist; async and cyclic methods/callback interfaces are real surfaces; callback dispatch distinguishes `IDispatch` and dual/vtable paths; cyclic IDs/requests and cyclic objects have explicit create/free paths; critical sections and timer APIs participate in module behavior.
- **Medium confidence:** cyclic owner maintains a linked list at `this+0x0c`; each list node stores a cyclic pointer at `+0x08`; cyclic state/flags occupy offsets around `+0x74`/`+0x80`; cyclic data and alternate data pointers are around `+0x38`/`+0x40`. This is supported by repeated direct accesses but lacks constructor-complete field tracing.
- **Low confidence/unresolved:** callback pointer storage offset, whether callback `IUnknown` is AddRef'd, whether request records hold a strong owner reference, exact `CCyclicID` versus `ReqID` nesting, destruction ordering under cancellation, timer owner, worker/apartment identity, and cross-apartment marshaling. Preserve these as open lifetime questions.

## Lifetime model to retain

The safe static model is: a COM-facing `CVar2`/`IVar` object can create async transaction or cyclic request state; a request/cyclic ID is tracked by an owner list and can be removed explicitly; callback notification may occur through `IDispatch` or dual/vtable dispatch; release/cancellation can produce an `E_ABORT` record even after the initiating COM object is released. Do not collapse `free CCyclicID/ReqID`, `free CCyclic`, or `Com-Object released or Async-Transaction cancelled` into proof of a complete reference-count protocol. The binaries explicitly leave callback-pointer checking and several ownership edges unresolved.
