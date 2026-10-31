# Stage 16.7 Iteration 2 Acceptance

## Verdict

**PARTIAL / NOT COMPLETE.** Independent review: **Verified with limitations**. No runtime/hardware claim is made.

## Objective disposition

1. **COM vtable entrypoints: VERIFIED STATICALLY for requested methods.** COFF ATL vftable symbols and raw `.rdata` words establish IVar and IVar2 arrays in both exact DLLs. Slots 9, 11, and 12 resolve to the `ReadVarAsync`, `ReadVarCyclic`, and `RemoveCyclicVariables` bodies listed in `entrypoints/iter2/VTABLE_MAP.json`. The tightened verifier checks hashes, vtable pointer words, and that each target is inside an executable PE section. Current run: `PASS`, 12 targets. This does not establish a runtime `QueryInterface`/object-construction invocation, though FinalConstruct's ATL interface map evidence is preserved separately.

2. **Callback path: PARTIALLY VERIFIED; request-specific delivery unresolved.** Public async and cyclic bodies call `CRequestID::MakeCB`; `MakeCB` constructs callback-result/VARIANT state and contains an indirect call through object vtable slot `+0x1c` (old `0x10013ad2`, new `0x10013bdc`). The exact object provenance and interface/method at that slot are not identified. The separate `GetIDsOfNames("OnDataChanged")` and `Invoke`-shaped sites are evidenced, but their use by a specific async transaction/cyclic subscription is not joined. No runtime delivery is claimed.

3. **ReqID lifecycle: PARTIAL; numeric creation/registration/lookup unresolved.** Caller output pointer is stored at transaction `+0x98`; transaction pointer is separate at wrapper `+0x04`; scalar `+0x20` is tested/logged but not causally identified with the generated/caller-visible ReqID. A full instruction scan found 11 old and 31 new candidate `+0x20` field uses and no `+0x98` reads in executable sections beyond the known storage; this narrows but does not prove the lifecycle. See `reqid/iter2_field_use_scan.json`.

4. **Cyclic scheduler/removal: PARTIAL; full causal chain unresolved.** Verified public cyclic methods enter internal reader/remover paths. Internal readers walk owner list nodes and directly call `CCyclic` constructors with owner-relative list arguments; constructor-side insertion is inferred, not established. `CBOnIdle` processes idle-list work, and `CCyclicID::IdleCB` has a vtable entry. However `DataChange` and `FlushCyclics` symbol starts overlap/misdecode; no direct owner-linked chain proves `DataChange -> idle enqueue -> CBOnIdle -> IdleCB -> FlushCyclics -> specific callback`. Removal traversal is visible, but match/unlink/delete/free remains unresolved.

## Independent review and contradictions

An earlier conservative relocation scan `/root/PL/stages/stage16_7/entrypoints/iter2/RELOCATION_VTABLE_MAP.json` has null targets and is superseded for slots 9/11/12 by the COFF-symbol-plus-raw-vtable evidence in `VTABLE_MAP.json` and `vtable_verification.json`. A separate delegation incorrectly transcribed old IVar2 slot 11 as `0x1001093e`; raw table word and independent verifier establish `0x1000f93e`. The code at `0x1001093e` is a different interior/shared region and is not the old IVar2 slot target.

The independent reviewer checked current iter2 arrays and confirmed the requested slot targets. Reviewer caveat: vtable bytes establish table slot values and decorated target identities, but not runtime COM instance construction. The verifier's prior target-range predicate was permissive; it was replaced with explicit executable-section membership and re-run successfully.

## Evidence and verification

- Canonical vtable map: `entrypoints/iter2/VTABLE_MAP.json`
- Raw tables: `entrypoints/iter2/{old,new}_{ivar,ivar2}_vtable_raw.txt`
- Exact slot checker: `entrypoints/iter2/verify_vtables.py`
- Captured result: `evidence/iter2_vtable_verifier_stdout.json`
- Independent audit: delegation `deleg_84549c5e`, verdict `Verified with limitations`; independently ran `verify_vtables.py` successfully (12/12), confirmed both DLL hashes, and inspected the current canonical iter2 map and callback/ReqID/cyclic raw evidence.
- An earlier independent review `deleg_c5f1e63c` also verified the slot words; its verdict is retained as historical corroboration.

No Windows/PCU execution, DDE/NCDDE, source archive edits, collector work, or runtime tests were performed.

## Closeout

Stage 16.7 remains open/partial because objectives 2-4 are not complete. Current engineering-safe acquisition path remains the historically runtime-proven synchronous batched `ReadVar`; async/cyclic behavior must remain capability-gated pending additional static linkage or authorized runtime evidence.
