# Stage 16.6 cyclic causal-edge follow-up

## Scope

Offline static analysis only; binaries unchanged. No DDE investigation or Windows tooling. Exact inputs:

- Old `MCVar.dll`: `/root/PL/PCU_old/H/mmc2/MCVar.dll`, SHA-256 `43a5c1991d98b6b6e155233a0114d7ff72bf4dec7edf58d0607da501e7d98712`.
- New `MCVar.dll`: `/root/PL/PCU_new/C/RECYCLER/S-1-5-21-4025392478-4199590385-3038547483-1005/Dc28/files/F/mmc2/MCVar.dll`, SHA-256 `5e7d955ebe7cfd52424b04e91471b7408f42bf6cc427e3d94c50bc7f4428c24a`.

Used GNU `objdump` for raw x86 decoding, Rizin for symbols/functions, and Capstone 5.0.7 to independently scan `.text` for direct relative calls. Preferred image base is `0x10000000` in both images. The prior stage's ownership report and `CYCLIC_LIFECYCLE.md` were treated as hypotheses, not as substitute evidence.

## Verified direct evidence

### FlushCyclics -> cyclic object/layout

In the new image, the named `CCyclicID::FlushCyclics(int)` entry is `0x10012e91`; the pre-existing disassembly and raw bytes agree that the body continues through at least `0x100134da`. Within its list loop:

- `0x1001300b: 8b 46 0c` loads `[ESI+0x0c]` as the initial list pointer.
- `0x1001302b: 8b 78 08` loads a candidate object pointer from `[EAX+0x08]`.
- `0x1001302e: 8b 00` loads the next pointer from `[EAX]`.
- `0x10013036: 8b 47 74` reads `[EDI+0x74]` from the candidate object.
- `0x1001305c: 8d 47 38` and `0x10013061: 8d 4f 40` form addresses `[EDI+0x38]` and `[EDI+0x40]`; conditional select uses one as a value source.

This validates the narrow layout claims: owner/list-head field at `this+0x0c`; list node's next link at node+0 and object pointer at node+8; candidate cyclic object is dereferenced at +0x74, +0x38, and +0x40. It does not establish a complete C++ struct, field names, size, or ABI stability.

The new `FlushCyclics` also directly tests bits in `[ESI+0x28]` and reads corresponding owner fields at `+0x44`, `+0x4c`, `+0x50`, `+0x54`, `+0x58`, `+0x5c`; don't assign semantic names beyond observed accesses. Old `FlushCyclics` shows the same function pattern with owner `[this+0x0c]`, list-node `+0/+8`, and cyclic object offsets `+0x74`, `+0x38/+0x40` (e.g. bytes at old VA `0x10013002..0x1001306f`). The binaries therefore independently support the repeated list/layout pattern.

### FlushCyclics -> callback helper

In the new image, the body at `0x1001343e` tests `0x80000` in `[ESI+0x28]`; when set, it pushes six constructed data pointers/arguments and calls `0x100139c2` directly at `0x100134ab` (`e8 12 05 00 00`, target `0x100139c2`). This is the same helper separately identified in stage16.5 as containing `OnDataChanged` dispatch diagnostics. The prior direct-call xref report captures helper references to callback names as DATA operands, not call xrefs, so this establishes a direct `FlushCyclics -> helper` edge, but **not** that this helper is definitely the cyclic `OnDataChanged` callback path or which indirect interface slot is invoked. It does establish that a path through the helper is conditionally reachable from FlushCyclics.

No direct relative call from the scanned `.text` targets the symbol VAs listed for `DataChange`/`IdleCB`/`FlushCyclics` in either build. This is not proof of absence of indirect calls: virtual dispatch, function-pointer calls, adjusted entry points, and misidentified symbol boundaries remain possible.

## Causal chain: exact boundary

- `CCyclicID::DataChange` to pending state: **unresolved**. The old symbol VA `0x10012b4c` begins `ff 8b 45 e8 66 81 ...`; the new symbol VA `0x10012c5e` begins `0f 81 ce 00 20 00 ...`. These bytes decode as implausible control flow, not reliable function prologues. Existing diagnostic strings (`susp`, `pend`) do not prove which fields are written or which branch queues work.
- `IdleCB` to `FlushCyclics`: **unresolved**. Old `IdleCB` symbol VA `0x10012c01` begins `e0 fe ff ff ...`; new VA `0x10012d13` begins `fe ff ff 89 ...`. These symbol labels overlap the boundary of a large disassembled region (Rizin labels parts of it as IdleCB, ShowState, GetError, FlushCyclics); neither direct-call scan nor boundary bytes support a trustworthy standalone IdleCB body/call edge.
- `FlushCyclics` to callback helper: direct call exists in new build at `0x100134ab -> 0x100139c2`, conditional on owner state bit `0x80000` at `[this+0x28]`. The helper's dispatch strings make it a candidate callback-dispatch helper, but the indirect call target/interface and exact argument meaning remain unproven.
- Old build: FlushCyclics named at `0x10012d7f`; raw bytes at the symbol begin `60 ff ff ff ...` and the initial decode is not trustworthy. No direct-call scan establishes DataChange/IdleCB-to-Flush linkage. Callback helper at `0x100138b8` is evidenced by prior report, but a cyclic caller edge is not established in this follow-up.

Therefore the complete causal claim `DataChange -> pending -> IdleCB -> FlushCyclics -> callback` is **not resolved**. Strongest defensible endpoint is: new FlushCyclics traverses a linked list of cyclic objects, creates callback-shaped data, and conditionally directly calls helper `0x100139c2`; the causal connection from DataChange/IdleCB into that flush and the helper's exact indirect callback remain the precise unresolved boundary.

## Reproducibility / method caveats

- Rizin `pdf` at some decorated symbol addresses emitted invalid instructions. GNU `objdump` independently reproduced the invalid symbol-start bytes; Capstone confirmed no direct-call instructions in `.text` targeting the listed symbol addresses. Do not cite these symbol addresses as reliable function starts.
- Rizin's automatic function segmentation splits a large body at misleading labels. Only the byte sequences and local basic-block behavior stated above are treated as proven.
- All analysis was read-only on supplied binaries. No tests/runtime execution were applicable.
