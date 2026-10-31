# Stage 16.7 Evidence Reconciliation

## Inputs

- Old MCVar: `/root/PL/PCU_old/H/mmc2/MCVar.dll`
  - SHA-256: `43a5c1991d98b6b6e155233a0114d7ff72bf4dec7edf58d0607da501e7d98712`
  - PE32/i386, image base `0x10000000`
- New MCVar: `/root/PL/PCU_new/C/RECYCLER/S-1-5-21-4025392478-4199590385-3038547483-1005/Dc28/files/F/mmc2/MCVar.dll`
  - SHA-256: `5e7d955ebe7cfd52424b04e91471b7408f42bf6cc427e3d94c50bc7f4428c24a`
  - PE32/i386, image base `0x10000000`

Verified tools: Rizin 0.10.0, GNU objdump 2.44, Python 3.13, pefile 2024.8.26, Capstone 5.0.7, Ghidra headless, Graphviz. Git is not used. No Windows runtime, PCU, DDE, or executable build is in scope.

## Starting corrections

- Old `0x1000fef1` / new `0x10010003`, vtable `+0x14`, is an `IDispatch::GetIDsOfNames`-shaped call resolving UTF-16 `OnDataChanged`. It is not direct delivery.
- Separate old `0x100146a0` / new `0x100147aa`, vtable `+0x18`, is an `IDispatch::Invoke`-shaped static callsite with a DISPID-like local and nearby callback diagnostics. Runtime success and request reachability are unknown.
- The target TypeLib count is 32 direct function records across eight TypeInfos and 92 across all 28 TypeInfos, per old/new decoded records.
- Old/new `ReadVarAsync` addresses `0x1000d28a` / `0x1000d39c` remain entry candidates with high entry confidence but uncertain contiguous body extent. Legacy `0x1000d3f6` / `0x1000d508`, DataChange, IdleCB and Flush labels are not accepted as clean standalone entries.
- Transaction `+0x98` stores caller `pReqID` pointer; it is not the numeric ReqID. Registration, numeric generation, lookup and cleanup remain open.
- Cyclic list/object accesses and new-build `0x100134ab -> 0x100139c2` conditional edge are local static evidence only; the complete scheduler chain is open.

## Superseded evidence

Stage16.5 maps and reports are preserved. Their mistaken `+0x14` delivery interpretation, 33-method count, legacy forwarding-thunk claim and unvalidated function-boundary claims are superseded by Stage16.6 correction artifacts.

## Stage16.7 gate

All new claims must be tied to vtable/data pointers, valid instruction boundaries, direct callsites or explicit dataflow. Strings, TypeLib names, generic imports and automatic function labels are candidate anchors only.
