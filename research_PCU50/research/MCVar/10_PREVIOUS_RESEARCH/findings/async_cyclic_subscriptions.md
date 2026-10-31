# MCVar Subscription and Event Capabilities

## Verdict

Native MCVar push/event delivery is **UNKNOWN, not proven**. The embedded TypeLib and static method names prove a named async/cyclic/callback surface, including `ReadVarAsync`, `ReadVarCyclic`, `RemoveCyclicVariables` and callback names such as `OnDataChanged`. They do not prove exact Automation signatures, connection points, `Advise`/`Unadvise`, callback delivery or live usability.

The SDK therefore implements only an explicitly labeled `POLLING_BACKED` subscription abstraction. Its tests are mock/offline tests, not PCU event validation.

## Evidence

- `RAW_EVIDENCE/old_TYPELIB_1_1033.bin` and `new_TYPELIB_1_1033.bin` are embedded MCVar resources.
- `MCVAR_API_REFERENCE.json` catalogs named async/cyclic methods and callback interfaces with unresolved signatures.
- No reviewed MCVar call/xref evidence proves `IConnectionPointContainer`, `FindConnectionPoint`, `IConnectionPoint::Advise`, `Unadvise`, source IID/vtable or event dispinterface metadata.
- DDE `XTYP_ADVSTART`/`DdePostAdvise` evidence belongs to DDE components and is not proof of an MCVar COM event source.

## Models

| Model | Status |
|---|---|
| Native MCVar COM event source | UNKNOWN |
| MCVar asynchronous request callback | PROVEN_STATIC name only; runtime UNKNOWN |
| `ReadVarCyclic` native cyclic delivery | PROVEN_STATIC name only; runtime UNKNOWN |
| DDE ADVISE exposed by MCVar | UNKNOWN / not joined to MCVar public API |
| Internal event source with polling | UNKNOWN |
| No usable native subscription; application polling required | NOT FALSIFIED; safest current implementation assumption |

## Polling fallback

`MCVAR_SDK/core/polling.py` and `MCVAR_SDK/acquisition/mcvar_sdk.py` provide bounded polling, initial/change-only delivery, cancellation and timeout handling. The application must label this mode `polling`, use local observation timestamps only, and avoid claims about source freshness, atomicity or backend transaction count.

## Required live discriminator

On an authorized matching Windows PCU, extract TypeInfo and inspect `IMPLTYPEFLAG_FSOURCE`, query `IConnectionPointContainer`, enumerate connection points, and run one bounded async/cyclic read with explicit removal. Record callback thread, timestamps, values, errors and cleanup. No such test was executed in this phase.
