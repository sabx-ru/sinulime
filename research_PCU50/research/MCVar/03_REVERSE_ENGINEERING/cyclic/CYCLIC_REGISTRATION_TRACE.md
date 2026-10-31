# Cyclic Registration and Removal Trace

## Scope and method

Offline static analysis of the supplied old/new PE32 i386 `MCVar.dll` images at preferred base `0x10000000`. Public entry bodies were identified from the exact vtable slots and Ghidra function map, then checked with `objdump -d -Mintel` and Rizin analysis. No runtime, Windows, or DDE testing was performed. **DIRECT** below means a raw instruction proves the edge/data access; it does not assign high-level semantics beyond the operands/call boundary.

## Public entry to internal reader

| Version | Public `ReadVarCyclic` (`IVar2`) | Internal direct call | Internal `RemoveCyclicVariables` target |
|---|---:|---:|---:|
| Old | `0x1001093e` | `call 0x10010cbf` at `0x10010b99` | `0x10010a94` |
| New | `0x10010a50` | `call 0x10010dd1` at `0x10010caa` | `0x10010ba6` |

The public reader body prepares its normalized flags/arguments and directly calls `InternalReadVarCyclic`; the public removal body `0x10010a94` old / `0x10010ba6` new is a short parameter-conversion/dispatch wrapper with a `MakeCB` call. Its direct following target is the internal removal implementation (`0x10010cbf` old / `0x10010dd1` new), where selection and cyclic object-list processing occurs. The new image's Ghidra function references and independently disassembled addresses agree. The known matched IVar2 vtable slot mapping is recorded in `entrypoints/COM_VTABLE_ENTRYPOINTS.md`; these are not names inferred from diagnostics alone.

## Registration: internal read to object and list

Both internal readers contain a per-variable loop starting at old `0x10010e54`, new `0x10010f66`. It loads a list node's object from `[node+8]` (`esi`), advances to `[node]`, and checks cyclic-record state via `[object+0x80]`. For a variable needing registration, the old body calls `0x100119a2` (`CCyclic` constructor) at `0x100100a9`; the matched new constructor is `0x10011ab4`, called at `0x100101bb`. The `this` argument is the list expression `&[CCyclicID+0x84]` (old `0x100100df..0x100100e8`; new `0x100101e1..0x100101fa` computes/pushes the corresponding owner field and passes its list node/parameters). Constructor symbols encode `CList<CCyclic>*` and `CCyclicID*` parameters.

The constructor-call edge is direct, but constructor-side insertion is **not established** by the available `CCyclic` body slice: the entry disassembles into a bounded rate-adjustment helper and the symbol/function boundary overlaps neighboring labels. Ghidra reports a direct constructor call from the internal read loop, and the decorated constructor signature accepts `CList<CCyclic>*` and `CCyclicID*`; the caller computes/passes the owner-relative list expression at `CCyclicID+0x84`. The exact list mutation/insertion instruction must not be asserted until the remainder of the constructor/list helper is resolved. Thus the proven chain is public read -> internal reader -> loop -> direct CCyclic-constructor call with the owner-relative list argument; list insertion is strongly indicated by type/signature but remains inferred rather than instruction-proven. This note does not assert a complete owner layout.

In contrast, `StartCyclics` (`old 0x100115f3`, `new 0x10011705`) performs array/handle selection work. Its outer body calls an internal helper at old `0x10011727` / new `0x10011839`, where code examines existing records via owner `[+0x74]` and node object at `+8`; the label range includes overlapping helper boundaries. It is not itself the observed `CCyclic` constructor-call site.

## Removal: what is and is not closed

The internal removal body begins old `0x10010cbf`, new `0x10010dd1`. It walks cyclic owner nodes using `node+8` and `node+0` (old around `0x10010e54..0x10010e67`, new `0x10010f66..0x10010f79`), and reads the candidate cyclic object's `+0x80` state. The public method passes request/selection context into this body. These are direct list traversal facts, not proof of a specific name/server-handle match or that a found node is detached.

The public removal wrapper's latter region performs idle-list-related target field testing/storing and calls helpers (new `0x10011c09..0x10011c57`; old counterpart `0x10011af5..0x10011b45`). The visible direct calls include list/cleanup helpers, but do not form a direct call to `CCyclicID::Delete(CCyclic*)`. A named Delete body exists in the new image at `0x1001166e`; no direct call from the public/internal removal path to it is established. Therefore exact node unlink, per-record deletion/free, and empty-owner destruction remain **unresolved** in both builds.

## Cross-version status

The matched reader and remover paths retain the same broad structure with the new image's recurring `+0x112` relocation. Both public readers call their internal reader; both internal readers loop over owner-list nodes and construct `CCyclic` records with the owner list argument. Removal wrappers/internal functions have corresponding selection/list traversal shapes and cleanup/idle-list logic. This supports structural similarity, not complete semantic equivalence: record selection precedence, rollback, list detach/free, ID lookup, and owner lifetime after final removal remain unproven.

## Focused evidence files

- Ghidra function/reference exports: `../evidence/ghidra_old_xrefs.txt`, `../evidence/ghidra_new_xrefs.txt`.
- Verified old/new `IVar2` method/vtable mapping: `../entrypoints/COM_VTABLE_ENTRYPOINTS.md`.
- Removal boundary and outstanding questions: `REMOVE_CYCLIC_LIFECYCLE.md`.
- Earlier cyclic layout limitations: `../../stage16_6/cyclic/CYCLIC_OBJECT_LAYOUT.json`.
