# Stage 15 Evidence Ledger

Scope: MCVar asynchronous/cyclic capability and read-only collector foundation. Source archives are immutable inputs; DDE/NCDDE work is frozen.

| ID | Class | Claim | Evidence | Status |
|---|---|---|---|---|
| E15-01 | RUNTIME | Synchronous `ReadVar` batches of 1..20 worked on PCU50.3 Windows XP x86; per-item quality/errors preserved in prior runs. | `/root/PL/research/MCVar/FINDINGS_AND_OPEN_QUESTIONS.md:7-11` and referenced phase logs | CONFIRMED_RUNTIME |
| E15-02 | STATIC | Old MCVar PE32/i386 SHA-256 is `43a5c1991d98b6b6e155233a0114d7ff72bf4dec7edf58d0607da501e7d98712`; timestamp 2004-06-23; image base `0x10000000`. | `reverse/rizin_old_inventory.txt`, direct `sha256sum`, `objdump -x` | CONFIRMED_STATIC |
| E15-03 | STATIC | New MCVar PE32/i386 SHA-256 is `5e7d955ebe7cfd52424b04e91471b7408f42bf6cc427e3d94c50bc7f4428c24a`; timestamp 2011-07-25; image base `0x10000000`. | `reverse/rizin_new_inventory.txt`, direct `sha256sum`, `objdump -x` | CONFIRMED_STATIC |
| E15-04 | STATIC | Both DLLs contain embedded `TYPELIB/1/1033` MSFT resources of 19,732 bytes; extracted resources are preserved under research/MCVar/api/resources. | `evidence/typelib_hashes.sha256`, PE resource extraction output, `pe_resource_inventory.json` | CONFIRMED_STATIC |
| E15-05 | STATIC | Both DLLs contain strings for `ReadVarAsync`, `ReadVarCyclic`, `RemoveCyclicVariables`, `OnDataChanged`, and callback interfaces. | `reverse/rizin_old_inventory.txt`, `reverse/rizin_new_inventory.txt` | CONFIRMED_STATIC_NAME_ONLY |
| E15-06 | STATIC | New and old images contain implementation diagnostic strings indicating request IDs, cyclic IDs, server/client handles, requested update rate, deadband/critical flags, data-change dispatch and callback HRESULT logging. | focused Rizin string inventory in `reverse/rizin_*.txt` | CORRELATED_STATIC; ABI unresolved |
| E15-07 | STATIC | Previous research did not prove exact IIDs/DISPIDs, parameter directions, SAFEARRAY declarations, connection-point behavior, callback delivery, or live native subscription. | `/root/PL/research/MCVar/FINDINGS_AND_OPEN_QUESTIONS.md:25-29`; `findings/async_cyclic_subscriptions.md:5-14` | CONFIRMED_OPEN |
| E15-08 | DESIGN | Current safe implementation mode is synchronous/polling-backed with a generic adapter seam; native async/cyclic must remain optional until TypeInfo/runtime proof. | prior collector architecture plus Stage 15 implementation lane | ACCEPTED_CONSERVATIVE_MODEL |

Rules: static names/diagnostic strings are not ABI or runtime proof. No PCU async/cyclic execution occurred in this Debian session. No write-capable MCVar method is invoked by Stage 15 artifacts.
