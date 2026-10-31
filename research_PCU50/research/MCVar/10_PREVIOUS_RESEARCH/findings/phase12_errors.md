# COM and Error Semantics

## Observable `ReadVar` contract

The preserved experiments show that `MCVar.Var2` exposes an Automation `ReadVar` path accepting scalar BSTR and `SAFEARRAY(BSTR)`. Tested arrays include sizes through 20, non-zero lower bound 1, reversed order and duplicates. Output arrays preserve per-position results; partial item errors can coexist with outer `HRESULT=S_OK`. Dynamic values in one batch can differ, so snapshot atomicity is not established.

Invalid `SAFEARRAY(VARIANT)` shape returns observed `0x80070057`. All-invalid examples can produce `DISP_E_EXCEPTION`/`0x81000303`-class behavior; error cases include `0x85000903`. Exact COM aggregate branches and provenance are not recovered.

Successful quality is normally observed as `0x00C0`; its producer is unknown. `pTimeStamps` and `pServerInfos` were observed as `VT_ERROR` with `0x80020004`; why they are omitted is unknown.

## Static boundaries

- Old `ReadVar` body begins around `0x1000BC30`; request/error-preparation call `0x1000BD47 -> 0x1000C532`.
- New counterpart `0x1000BE59 -> 0x1000C644`.
- The branch at old `0x1000BD4F..0x1000BD73` compares helper/status values and dispatches cleanup/conversion helpers, but the complete CFG and accumulator semantics are not established.
- Nominal `DecodeError` symbol targets around old `0x10007CAF` / new `0x10007DBD` disassemble as cleanup/free/reset logic in the reviewed slices; they are not accepted error producers.
- Cleanup `0x1000BDDC -> 0x10014CBE` and new `0x10014DC8` are not submission edges.

## Status by behavior

| Behavior | Evidence | Status |
|---|---|---|
| Scalar/BSTR and BSTR-array input | preserved invocation logs and COM observations | PROVEN_RUNTIME (tested cases) |
| Batch max tested | 1..20 elements, order/duplicate/lower-bound cases | PROVEN_RUNTIME for tested range; >20 unknown |
| Per-item errors | slots and mixed-error rounds | PROVEN_RUNTIME |
| Outer HRESULT | mixed can be S_OK; all-invalid can be exception | PROVEN_RUNTIME observations; exact rule UNKNOWN |
| Invalid array shape | 0x80070057 | PROVEN_RUNTIME observed |
| `0x81000303`, `0x85000903` origins | no full producer/dataflow | UNKNOWN |
| Quality `0x00C0` source | observed output only | UNKNOWN |
| CacheDevice 0/1/2 | modes accepted in tests | semantics UNKNOWN |
| Timestamp/server-info | VT_ERROR 0x80020004 observed | cause UNKNOWN |
| Atomic snapshot | changing values observed in batch | not guaranteed; implementation mechanism UNKNOWN |

## Error provenance alternatives

For `0x81000303` and `0x85000903`, viable sources include MCVar mapping/lookup, another Siemens module, an NCDDE/NC-origin code propagated through a response, arithmetic composition, or a lookup table. Literal absence in selected binaries does not distinguish these. No link to CF_OEMTEXT failure is accepted.

## Smallest decisive test

On an authorized isolated Windows snapshot, trace one valid, one invalid, one mixed, and one all-invalid ReadVar call through entry/return and output SAFEARRAY stores. Record caller RVA, helper return values, pErrors/pQualities writes, optional output VARIANT types, and message/DDE API ancestry. For CacheDevice, repeat a fixed dynamic item across 0/1/2 in fresh and persistent sessions. Do not use a changing wall clock as source-timestamp proof. No such runtime trace was run in this phase.
