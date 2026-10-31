# RemoveCyclicVariables Lifecycle

## Scope and confidence

Offline static analysis only. Inputs are the exact old/new images identified by SHA-256 in `../reports/EVIDENCE_RECONCILIATION.md`. This note distinguishes direct code behavior from API shape and diagnostic strings. It does not reconstruct a complete deletion transaction where call/dataflow evidence is absent.

## Public operation

`IVar`/`IVar2` expose `RemoveCyclicVariables` with a request identifier and variant-array selection/output parameters (see prior TypeLib decode). Diagnostics include `Invalid ReqID` and removal method traces, but neither those strings nor the public signature establish matching precedence, empty-array behavior, or cleanup semantics.

## New image: direct idle-list/cleanup behavior

At `0x10011ba6`, the `CVar2::RemoveCyclicVariables` method's CFG includes a thread-idle-list maintenance region:

1. It tests `[edi+4]` at `0x10011c09`.
2. If zero, it logs the target as being added to the thread idle list, then stores `esi+0x2c` into `[edi+4]` at `0x10011c23`.
3. When that field value is nonzero, it calls `0x100021c9` with `edi` at `0x10011c2a`.
4. It then calls `0x10001104` with `&[edi+8]` at `0x10011c33`.
5. If `[edi+4]` was already nonzero, it follows the alternate already-in-list diagnostic branch and does not perform the store/call sequence from step 3 on that path.
6. A later condition on `[esi+0x4c]` controls another direct call to `0x10001673` with `esi` (`0x10011c4b..0x10011c52`). Its precise destructor/cyclic-removal meaning is not established from this local sequence alone.

This is sufficient to state that removal processing can register or reuse an idle-list target and invoke cleanup helpers on a target-associated object. The target is not conclusively identified as `CCyclicID::IdleCB`, a timer, or a per-variable `CCyclic` destructor. Do not turn this into a proven scheduler callback sequence.

## Object ownership and deletion boundary

Prior evidence supports an owner/request object (`CCyclicID`) with a list of cyclic records (`CCyclic`) and a named `CCyclicID::Delete(CCyclic*)` helper. The exact per-call removal path from a selected RequestID/name/handle through list matching, record unlinking, `Delete`, free, and destruction of a now-empty owner was not verified. The new wrapper's direct idle-list calls do not fill this gap. Old-build per-record deletion equivalence is likewise unproven.

The request identifier passed to the public operation is selection context; it must not be conflated with the stored caller `pReqID` pointer known from the independent async transaction analysis. No claim is made here about ReqID numeric generation or object lookup.

## Lifecycle graph

`RemoveCyclicVariables API -> (request/selection processing) -> cyclic record removal -> CCyclicID::Delete -> free CCyclic / possibly owner cleanup` remains partly inferred/unresolved as a chain. Directly observed in the new build is the API implementation's idle-list target field test/store and calls to `0x100021c9`, `0x10001104`, and conditionally `0x10001673`. Full edge evidence/status is in `CYCLIC_LIFECYCLE_GRAPH.json`.

## Explicitly unresolved

- Which of names, server handles, client handles, or their combination takes precedence.
- Whether null/empty arrays mean remove all, remove none, or reject.
- Whether a missing ReqID is rejected before any mutation on all paths.
- Which exact node/record is detached on each success/error path.
- Whether one removed record leads to `CCyclicID::Delete`, and whether the owner survives zero records.
- Whether removal cancels any timer/idle callback or waits for one already queued.
- Whether old and new implementations have equivalent removal semantics.

## Evidence anchors

- New `CVar2::RemoveCyclicVariables`: `0x10011ba6`; idle-list local block `0x10011c09..0x10011c57`.
- Named new `CCyclicID::Delete(CCyclic*)`: `0x1001166e`; caller relationship to the public removal implementation is not established in this note.
- Corrected preceding lifecycle/evidence map: `../stage16_6/cyclic/CYCLIC_LIFECYCLE.md`, `../stage16_5/cyclic_flow/followup/STAGE16_6_CYCLIC_CAUSAL_EDGES.md`.
