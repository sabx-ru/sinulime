# Research milestones and interpretation changes

This timeline captures how the evidence progressed. It is not a changelog of Siemens components.

## Before 2026-11-10 — Working MCVar / initial NCDDE experiments

A separate, XP-compatible MCVar monitor displayed real machine values on a test PCU50. Earlier NCDDE/DDE experimentation had confirmed selected service names and binary framing. Some X-axis live values aligned with HMI Advanced, while Y-axis reporting and drive-current scaling/physical-axis binding remained unresolved. A separate drive-alarm incident was reported after a previous DDE experiment; causality was not proven. Those legacy codebases and their raw captures are not redistributed here.

## 2026-11-10 — Static PE and mapping investigation

Independent analysis identified `MCVar.Var2`/DDE-related internals, original `.NSK` definitions for General/Channel/Axis/Drive MD, and concrete static callsites between `ibdrv.exe`, `sllist.dll` and `slacx.dll`. Within `slacx.dll`, a table of 22 map entries and a generator for `LINK(...)` records were reconstructed. Archived General/Channel/Axis `.NSK` files contained 1,711 records matching the recovered structural template.

A crucial limitation emerged: **generating `.NSK` descriptions is not the same as reading live MD values**. The runtime path from a particular HMI MD selection to DDE transport remained unproved. DCTL's general DDE request and receive handlers were separately identified.

## 2026-11-11 — New Win32 DDEML test client validated on PCU50

A minimal C client, built from Debian for Windows XP x86, requested **one configured item per invocation** using `ncdde|machineswitch` and `ncddeBinary`. Eight test logs contained actual returned binary frames. General, Channel, Axis and one Drive MD were successfully decoded offline and checked against known historical mapping declarations. The same General MD 10050 was returned identically by both `*_tea` and `*_pre` forms.

This direct independent test means that reading **some** MD values does not require a completed reverse engineering of `ibmd.exe`; however, it does not establish a universal MD API. The main follow-up work shifted to type-safe decoding, validated indexing and one controlled PLC-bit test, not untargeted HMI disassembly.

## Claims that have **not** changed

Universal MD access, exact X/Y index semantics, PLC reads by this test client, actual drive-current monitoring, server cache behavior, and complete HMI-to-NCDDE runtime data flow are still unverified. The 2026-11-11 drive reply does not close the earlier safety questions.

See [evidence-ledger.md](evidence-ledger.md), [field-tests.md](field-tests.md) and [static-research.md](static-research.md) for the evidence categories.
