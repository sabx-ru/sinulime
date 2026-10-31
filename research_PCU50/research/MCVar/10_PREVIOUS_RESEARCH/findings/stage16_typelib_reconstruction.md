# Stage16: Exact TypeLib Recovery Design

## Stage15 checkpoint and evidence boundary

The available repository materials do not contain a Stage15-labeled result or output. The artifacts currently available are `api/resources/old_TYPELIB_1_1033.bin` and `new_TYPELIB_1_1033.bin` (both 19,732 bytes; distinct hashes in `api/COM_API_REFERENCE.json`), registry resources, the static API reference, and a Windows TypeInfo probe source/binary. Accordingly, this design does not claim Stage15 decoded any signature.

Encoding-decoded/static evidence in the current reference: embedded TypeLib and decorated-name/string evidence includes `ReadVarAsync`, `WriteVarAsync`, `ReadVarCyclic`, `RemoveCyclicVariables`, callbacks `OnDataChanged`, `OnWriteComplete`, `OnCommandCompleted`, and named callback interfaces. This proves names only. Existing evidence explicitly leaves exact IIDs, VARTYPEs, parameter directions, retval conventions, optionality, SAFEARRAY details, source-interface status, and event delivery unresolved. The binary resources differ, despite identical registration resources: decode both versions independently.

Inference (not yet evidence): callback arguments may be interface pointers and cyclic removal may take a subscription identifier. Do not encode these guesses into an ABI/schema. No DDE behavior is relevant to this recovery.

## Method

1. Freeze inputs: hash both resource files and associate each output with old/new DLL identity, TypeLib GUID/version/LCID, and resource hash. Never overwrite inputs. Retain parser version and raw offsets.
2. Parse the MSFT TypeLib container with a bounded, offset-checked parser. Resolve the directory/typeinfo records, names, member records, parameter element descriptors, referenced typeinfo indices, custom data, and function vtable offsets. Decode recursive `TYPEDESC` forms including pointers, SAFEARRAYs, CARRAYs and user-defined references. Preserve raw bytes/offsets beside interpreted fields; reject out-of-range, overlapping-impossible, cyclic/unbounded, or unsupported structures as unresolved rather than guessing.
3. Produce a normalized record for every target method and callback: interface name/GUID/typekind/flags; function ordinal; memid/DISPID; invocation kind; `CALLCONV`; `FUNCDESC.oVft`; return `TYPEDESC`; parameter order/name/type/`PARAMFLAG` bits/default constant; `cParams`, `cParamsOpt`; and referenced typeinfo identity. Keep `TYPEDESC.vt` separate from `ELEMDESC.paramdesc.wParamFlags`: VT alone does not establish `[in]`, `[out]`, `[in,out]`, retval, LCID, optional, or default semantics.
4. Independently extract the same records on Windows using `LoadTypeLibEx(path, REGKIND_NONE, ...)`, `ITypeLib`/`ITypeInfo`, `GetTypeAttr`, `GetFuncDesc`, `GetNames`, `GetDocumentation`, `GetRefTypeOfImplType`/`GetImplTypeFlags`, and release every descriptor/attribute. Do not register/activate/execute methods for the baseline dump. Compare canonical records field-by-field, not just rendered IDL or method names.
5. Correlate ABI evidence to source/binary: match interface IIDs and method names to ATL map/vtable construction, decorated C++ symbols, and call-site argument layout. For native vtable interfaces, derive slot index from `oVft / sizeof(void*)` only after validating pointer size/call convention and IUnknown’s three leading slots. Record DISPID order separately: dispatch order and vtable slot are not interchangeable. Use old/new images independently; no VA or slot carryover assumption.
6. Validate target scope first: async/cyclic methods and all callback interfaces/methods; then removal/cancellation-like members needed to establish lifetime. Record whether each callback interface is dual/dispatch/vtable and whether any coclass implementation flags mark it as source. Source metadata is not proof of a working connection point; runtime `IConnectionPointContainer` enumeration and bounded `Advise` test are a separate, authorized follow-up.

## Acceptance criteria

- Both resource hashes, TypeLib identity/version/LCID, and parser/runtime versions are recorded; old and new outputs are separate.
- For `ReadVarAsync`, `WriteVarAsync`, `ReadVarCyclic`, `RemoveCyclicVariables`, `OnDataChanged`, `OnWriteComplete`, and `OnCommandCompleted`, output includes complete interface identity and complete function descriptor: exact parameter count/order/types, recursive type details, all direction/retval/optional/default flags, return type, memid, invkind, calling convention, `oVft`, and computed slot where applicable. Unknowns are explicitly marked; no field is inferred from names.
- The Windows `LoadTypeLibEx(..., REGKIND_NONE)` oracle and offline parser agree exactly on all normalized fields for every target record, including `oVft`, parameter flags, recursive types and referenced typeinfo. Any disagreement blocks an “exact” claim and is triaged against raw bytes and OS output.
- Slot calculations are byte-aligned to pointer width, preserve declaration/interface ordering, and explain whether the interface is pure vtable, dual, or dispinterface; callback dispatch IDs must not be mislabeled as vtable slots.
- Code correlation independently supports each claimed interface/vtable association: GUID/IID, method order, slot offsets, and thunk/implementation correspondence are documented. Unmatched members remain unmatched rather than forced into a mapping.
- For any claim of source/event capability, TypeLib implementation flags and live Windows connection-point enumeration are reported separately. No claim of callback delivery without a bounded runtime callback observation and cleanup evidence.
- Regression fixture tests cover both version resources, malformed/truncated offsets, nested TYPEDESC references, alias/user-defined types, pointer and SAFEARRAY forms, and deterministic output. The parser never reads outside the resource or silently substitutes an unsupported descriptor.

## Offline MSFT parser risks

- MSFT is a compiler/runtime serialization format with version/layout variants; assumptions copied from one typelib can misparse another. Resource blobs are not standalone `.tlb` files, so PE resource extraction boundary and file-header assumptions matter.
- Record offsets and counts are untrusted. Wrong origin (resource start versus file start), alignment, signedness, or section-relative base can produce plausible but shifted records. Require bounds checks and raw offset reporting.
- `TYPEDESC` can nest and reference other typeinfos; flattening to the top-level `vt` loses pointer/SAFEARRAY/user-defined identity. Resolving HREFTYPE requires the correct owning typeinfo context.
- VARTYPE does not determine direction. Parameter flags are separate, and retval/out pointer conventions can be subtle. `cParamsOpt` alone does not identify which names/default values are present.
- `oVft` is a byte offset, not a slot number; dispatch IDs and function ordinals are different namespaces. Dual/dispinterface representations and inherited IUnknown/IDispatch slots require distinct handling.
- Names/strings can decode while the associated descriptor table is incomplete or misassociated. Successful name extraction is not signature completeness.
- Old/new TypeLib hashes differ; matching layouts or assuming the same IIDs/order from shared names may conceal version drift.
- Windows `LoadTypeLibEx` is the authoritative behavioral parser for these resources; static parsing remains a cross-check. The existing probe is insufficient as-is: it prints only top-level parameter `tdesc.vt` and omits direction flags, recursive descriptors, return type, calling convention, `oVft`, interface flags, references and HRESULTs from several calls.

## Deliverables and limits

Stage16 should deliver versioned JSON/TSV canonical dumps, raw-offset provenance, parser tests, Windows oracle output, a mismatch report, and code-correlation notes. The current Linux-side materials do not provide a Windows `LoadTypeLibEx` run; exact signatures and slot values therefore remain unverified until that oracle is run. No source implementation change or DDE investigation is in scope.
