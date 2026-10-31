# Stage 16.7 Report

## Status
**PARTIAL; NOT COMPLETE.** Work is a consolidation of supplied Stage16.7 artifacts and Stage16.6 reports. Offline static scope only. No new binary analysis, Windows execution, PCU/collector activity, or DDE work was performed.

## Consolidated findings

- **Entrypoints:** Old/new `ReadVarAsync` candidates at `0x1000d28a` / `0x1000d39c` share the captured entry prefix and directly call the shared starter. Concrete IVar/IVar2 vtable arrays, slot pointers, interface-subobject binding, and some function boundaries remain unbound. Do not call the entry candidates verified COM entrypoints.
- **Callbacks:** Both images contain `GetIDsOfNames("OnDataChanged")` at vtable `+0x14` and separate `Invoke`-shaped callsites at `+0x18`. Static dispatch shape is supported. Reachability from a specific async request or cyclic owner to the helper remains unresolved; runtime delivery/HRESULT and exact DISPPARAMS semantics are not established.
- **ReqID:** Caller `pReqID` is stored as a pointer at transaction `+0x98`; the wrapper `+0x04` separately stores the transaction pointer. A scalar at transaction `+0x20` is tested/logged, but its origin, relationship to the caller output, registration, and numeric-key lookup are unresolved.
- **Cyclic:** Flush-region list/object accesses are supported in both builds. The new build has a conditional call `0x100134ab -> 0x100139c2`, but no complete DataChange-to-scheduler-to-flush-to-delivery chain is established. The cyclic scheduler is incomplete; old equivalent helper caller is not proven.
- **Rates/comparison:** Available artifacts do not establish rate/filter semantics or semantic old/new equivalence. Matching labels and image section summaries are insufficient evidence.

## Verification

Verifier: `verification/verify_stage16_7.py` (path: `/root/PL/stages/stage16_7/verification/verify_stage16_7.py`). It was executed after consolidation with `python3 /root/PL/stages/stage16_7/verification/verify_stage16_7.py`.

Actual result: **PASS**. `verification/test_results.json` reports 10 checks passed: old hash, image base, entry bytes and direct call; new hash, image base, entry bytes and two direct calls; callback graph closure (29 nodes, 20 edges). This verifier does not test the unresolved gates above and is not a Stage completion result.

## Gate decision

Stage completion gates fail: entrypoints are unbound; callback request reachability is unresolved; ReqID origin/lookup is unresolved; cyclic scheduler is incomplete. Stage16.7 therefore remains **PARTIAL / NOT COMPLETE**.

Primary machine-readable artifacts: `EVIDENCE_LEDGER.json` and `FUNCTION_MAP.json`. Open questions and a bounded follow-on plan are in the companion reports.
