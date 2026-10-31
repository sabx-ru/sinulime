# Cyclic Scheduler Evidence

## Scope

Offline static analysis of the exact old/new `MCVar.dll` images listed in Stage 16.7 reconciliation. No executable, collector, Windows runtime, DDE, or binary writes. The existing Stage 16.6 corrected cyclic map is carried forward as a hypothesis ledger, then updated only where direct instructions or object/dataflow support a claim.

## Supported scheduler facts

- Both images contain a `CCyclicID::FlushCyclics(int)` region with the corrected linked-list traversal documented in `../stage16_6/cyclic/CYCLIC_OBJECT_LAYOUT.json`: owner `[this+0x0c]`, node `next` at `+0`, object at `+8`; cyclic candidate accesses at `+0x74`, `+0x38`, `+0x40`. These accesses prove flush-side processing, not what schedules entry.
- New image: within the flush region, `0x100134ab` directly calls `0x100139c2`, conditionally after testing bit `0x80000` in owner `[this+0x28]` at `0x1001343e`. This proves one guarded route to the helper; its eventual indirect callback is not proven to be this cyclic object's `OnDataChanged` invocation.
- New image: `CVar2::RemoveCyclicVariables` includes a path at `0x10011c0f..0x10011c33` which, when `[edi+4]` is zero, assigns `[edi+4] = esi+0x2c`, invokes `0x100021c9` with `edi` when that field is non-null, then calls `0x10001104` with `&[edi+8]`. The same routine branches to a log path when `[edi+4]` is already nonzero. These are direct observations of an idle-list-related target/reference and cleanup path occurring during removal. They do not, alone, establish what the target represents, who invokes it later, or a timer/message/work-queue cadence.
- The surrounding `CVarThreadState::CBOnIdle` symbol-label region overlaps a large function body. Its label, `IdleCB`, `susp`, `pend`, and `FlushCyclics` strings are not sufficient to infer a chain. Prior corrected analysis reports malformed DataChange/IdleCB label entries and no direct relative calls to the listed DataChange/IdleCB VAs.

## Causal boundary

No complete chain is established from `CCyclic::Data` through `CCyclicID::DataChange`, pending state, idle scheduling, flush, and callback. In particular, the removal-side idle-list manipulation cannot be used as evidence that `DataChange` enqueues work. No timer API, message posting, event signaling, or work queue is attributed to the cyclic object without a verified xref plus object dataflow. The only direct cyclic flush-to-helper edge is the conditional new-build call above; no equivalent old-build caller is established.

## Confidence summary

| Claim | Status | Basis |
|---|---|---|
| Flush region traverses owner list and candidate cyclic records | Direct, both builds | Corrected raw instruction accesses in `STAGE16_6_CYCLIC_CAUSAL_EDGES.md` |
| New flush region conditionally calls `0x100139c2` | Direct, new only | `0x100134ab` relative call; guarded by owner state bit |
| Removal path interacts with an idle-list target | Direct local behavior, new | `[edi+4]` test/store, `[esi+0x2c]` value, call `0x100021c9`, cleanup call `0x10001104` |
| Idle-list target is the cyclic periodic scheduler | Unresolved | Target identity and later dispatch dataflow not fully tied to cyclic owner |
| `DataChange -> IdleCB -> FlushCyclics` | Unresolved | Malformed/overlapping labels; no reliable causal call/dataflow chain |
| Timer/message/event/work-queue mechanism | Unresolved | No concrete cyclic-object-tied evidence recovered |
| Callback helper delivers this cyclic update | Unresolved | Direct helper call exists only in new image; indirect slot/arguments not resolved |

## Evidence references

- `../stage16_6/cyclic/CYCLIC_LIFECYCLE.md`
- `../stage16_5/cyclic_flow/followup/STAGE16_6_CYCLIC_CAUSAL_EDGES.md`
- New image `0x10011ba6` (`CVar2::RemoveCyclicVariables`) and `0x10012e91` (`FlushCyclics` label; inspect valid body region, not malformed adjacent labels).
- Old/new binaries and SHA-256 values: `../reports/EVIDENCE_RECONCILIATION.md`.
