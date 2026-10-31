# Track C: Batching Evidence and Alternative Models

## Scope and provenance

This analysis reuses the preserved phase11 corpus and its saved revalidation output. No PCU executable or live endpoint was called. Runtime observations are reported as recorded; interpretation beyond those observations is labeled inference/correlation. The machine-readable per-step evidence is in [`BATCHING_EVIDENCE.json`](BATCHING_EVIDENCE.json).

## Revalidation snapshot

The saved validator records 104 runner steps and 104 logs, 198 strict binary captures and 197 transitions. MC records contain 65 invocations requesting 606 elements, of which 604 were reported processed; 2 variant-array invocations reported zero processed. Across the 197 adjacent binary-response transitions, 197 matched the saved expected modulo delta and 0 did not. These are counts of observed records, not counts of transactions.

## Per-step MC evidence

| Step | Name | Rounds | Requested elements | Processed elements | Shape / notable status |
|---:|---|---:|---:|---:|---|
| 2 | A01_BATCH_01 | 1 | 1 | 1 | array-bstr x1 |
| 3 | A02_BATCH_02 | 1 | 2 | 2 | array-bstr x1 |
| 4 | A03_BATCH_03 | 1 | 3 | 3 | array-bstr x1 |
| 5 | A04_BATCH_05 | 1 | 5 | 5 | array-bstr x1 |
| 6 | A05_BATCH_07 | 1 | 7 | 7 | array-bstr x1 |
| 7 | A06_BATCH_10 | 1 | 10 | 10 | array-bstr x1 |
| 8 | A07_BATCH_15 | 1 | 15 | 15 | array-bstr x1 |
| 9 | A08_BATCH_20 | 1 | 20 | 20 | array-bstr x1 |
| 10 | A09_SCALAR | 1 | 1 | 1 | scalar x1 |
| 11 | A10_LOWERBOUND_1 | 1 | 1 | 1 | array-bstr x1 |
| 12 | A11_LOWERBOUND_5 | 1 | 5 | 5 | array-bstr x1 |
| 13 | A12_LOWERBOUND_20 | 1 | 20 | 20 | array-bstr x1 |
| 14 | A13_REPEAT_20 | 2 | 40 | 40 | array-bstr x1, array-bstr x2 |
| 15 | B01_REVERSE_5 | 1 | 5 | 5 | array-bstr x1 |
| 16 | B02_REVERSE_20 | 1 | 20 | 20 | array-bstr x1 |
| 17 | B03_DUPLICATE_LAST_20 | 1 | 20 | 20 | array-bstr x1 |
| 18 | B04_DUPLICATE_MIX | 1 | 5 | 5 | array-bstr x1 |
| 19 | B05_STATIC_20 | 1 | 20 | 20 | array-bstr x1 |
| 20 | B06_CLOCK_20 | 1 | 20 | 20 | array-bstr x1 |
| 21 | B07_CLOCK_20_REPEAT | 2 | 40 | 40 | array-bstr x1, array-bstr x2 |
| 22 | B08_DYN_MIX_20 | 1 | 20 | 20 | array-bstr x1 |
| 23 | B09_STRINGS_5 | 1 | 5 | 5 | array-bstr x1 |
| 24 | B10_DOUBLES_5 | 1 | 5 | 5 | array-bstr x1 |
| 25 | B11_INTS_5 | 1 | 5 | 5 | array-bstr x1 |
| 26 | B12_DOMAINS_5 | 1 | 5 | 5 | array-bstr x1 |
| 27 | B13_R_INDICES_5 | 1 | 5 | 5 | array-bstr x1 |
| 28 | B14_CLOCK_AND_R | 1 | 5 | 5 | array-bstr x1 |
| 29 | C01_ONE_BAD_FIRST | 1 | 5 | 5 | array-bstr x1 |
| 30 | C02_ONE_BAD_MIDDLE | 1 | 5 | 5 | array-bstr x1 |
| 31 | C03_ONE_BAD_LAST | 1 | 5 | 5 | array-bstr x1 |
| 32 | C04_BAD_TWO | 1 | 5 | 5 | array-bstr x1 |
| 33 | C05_ALL_BAD | 1 | 3 | 3 | array-bstr x1 |
| 34 | C06_BAD20_SPARSE | 1 | 20 | 20 | array-bstr x1 |
| 35 | C07_DUP_BAD5 | 1 | 5 | 5 | array-bstr x1 |
| 36 | C08_UNSUPPORTED_VARIANT | 1 | 1 | 0 | array-variant x1 |
| 37 | C09_RECOVER_AFTER_ERR | 1 | 20 | 20 | array-bstr x1 |
| 38 | D01_CACHE_STATIC_1 | 1 | 1 | 1 | array-bstr x1 |
| 39 | D02_CACHE_STATIC_0 | 1 | 1 | 1 | array-bstr x1 |
| 40 | D03_CACHE_STATIC_2 | 1 | 1 | 1 | array-bstr x1 |
| 41 | D04_CACHE_STATIC_1 | 1 | 1 | 1 | array-bstr x1 |
| 42 | D05_CACHE_CLOCK_1 | 2 | 2 | 2 | array-bstr x1, array-bstr x2 |
| 43 | D06_CACHE_CLOCK_0 | 2 | 2 | 2 | array-bstr x1, array-bstr x2 |
| 44 | D07_CACHE_CLOCK_2 | 2 | 2 | 2 | array-bstr x1, array-bstr x2 |
| 45 | D08_CACHE_CLOCK_1 | 2 | 2 | 2 | array-bstr x1, array-bstr x2 |
| 46 | D11_CACHE_CLOCK20_0 | 1 | 20 | 20 | array-bstr x1 |
| 47 | D12_CACHE_CLOCK20_1 | 1 | 20 | 20 | array-bstr x1 |
| 48 | D13_CACHE_CLOCK20_2 | 1 | 20 | 20 | array-bstr x1 |
| 74 | G01_MC_1 | 1 | 1 | 1 | array-bstr x1 |
| 76 | G03_MC_5 | 1 | 5 | 5 | array-bstr x1 |
| 78 | G05_MC_20 | 1 | 20 | 20 | array-bstr x1 |
| 80 | G07_MC_5_BAD2 | 1 | 5 | 5 | array-bstr x1 |
| 82 | G09_MC_ALL_BAD | 1 | 3 | 3 | array-bstr x1 |
| 84 | G11_MC_BAD_SHAPE | 1 | 1 | 0 | array-variant x1 |
| 90 | G17_MCV_20_REPEAT2 | 2 | 40 | 40 | array-bstr x1, array-bstr x2 |
| 97 | H06_MC_RECOVERY | 1 | 20 | 20 | array-bstr x1 |
| 100 | I01_MC20 | 1 | 20 | 20 | array-bstr x1 |
| 102 | I03_CLOCK20 | 2 | 40 | 40 | array-bstr x1, array-bstr x2 |

The full step ledger includes every runner step, with zero-element steps preserved. Requested/processed element counts come from the saved MC invocation logs parsed by phase11 revalidation. They count values in the call shape, not lower-level wire operations.

## Counter-delta interpretation

The saved sequence field is an 8-bit value. For each adjacent successful binary capture the evidence records `(next_sequence - prior_sequence) mod 256` and the sum of reported processed MC elements on steps strictly between those captures. Agreement is a cross-log correlation. It does not observe an API transaction counter, identify where the sequence is incremented, or establish one transaction per item/call. In particular, do not rename `actual`, `expected`, or `mc_elements` as transaction counts.

The baseline correlation in phase11 computes `expected = 1 + intervening processed elements`; this is a candidate relationship, not proof of its mechanism. The steps ledger and all 197 transitions are available in JSON for review.

## Alternative models H12-B1 through H12-B6

| ID | Model | Distinguishing prediction | Status from these logs |
|---|---|---|---|
| H12-B1 | One transaction per requested item | Delta scales with requested/processed element count rather than number of API invocations. | Fully processed batches imply a transaction count equal to element count. |
| H12-B2 | One transaction per ReadVar invocation | Each invocation increments counter once, independent of item-array length. | Delta should be 1 for all batch sizes. |
| H12-B3 | One transaction per accepted element | Only successfully processed slots advance counter; failed element slots do not. | Deltas track processed elements, diverging when item errors occur. |
| H12-B4 | One transaction per invocation plus processed elements | An invocation contributes one, plus each processed element. | Delta should be 1 + processed elements per call. |
| H12-B5 | One transaction per batch with variable-sized server work | Counter records a server work unit that might depend on cache, item type, duplicate/cyclic inputs, or request size. | Repeatable item/order/cache contrasts or non-linear deltas distinguish it. |
| H12-B6 | Counter is an unrelated modulo-256 event stream | Observed correlation can arise from another event source; delta is not transaction count evidence. | Would not consistently track intervening known calls in independently varied trials. |

The logged batch sizes (including singletons, batches through 20, repeated calls and rejected variant-array shape) provide useful contrasts. But there is no authoritative observation of transaction boundaries and the traces do not independently instrument server internals; the six models therefore remain alternatives to test, not claims that a counter increment means a transaction.

## Experiment matrix (offline design; do not run against a live PCU without separate authorization)

| Test | Contrast | Primary discriminant | Required observations |
|---|---|---|---|
| M1 | Single-item read vs arrays of 1, 2, 3, 5, 7, 10, 15, 20 | B1 vs B2/B4 | Independent invocation count and accepted slot count; sequence snapshots; repeats |
| M2 | Same array repeated, same session and fresh session | B5/B6 and state/reset effects | Session identity, sequence before/after, call-boundary timestamps |
| M3 | One known bad slot at first/middle/last; all-bad; duplicates | B1/B3/B5 | Per-slot HRESULT/status, accepted count, sequence observations |
| M4 | Unsupported array variant vs supported BSTR array | Call-count vs accepted-work behavior | Exact VARIANT type, HRESULT, per-element results, pre/post sequence |
| M5 | Fixed item set/order while varying cache mode 0/1/2 | B5 cache dependence | Cache setting confirmed by call and independent server-side instrumentation |
| M6 | Compare direct single-item reads with same items in one multi-read | B1 vs B2/B4 | API invocation boundaries and raw transport trace from a separately approved observer |
| M7 | Interleave unrelated operations/no-op controls and repeat across sessions | B6 unrelated-event hypothesis | Full event source attribution, sequence wrap handling, control runs |
| M8 | Repeat on isolated authorized simulator with documented instrumentation | Establish mechanism without production effects | Instrumentation definition, version, reset semantics, synchronized traces |

No matrix experiment was executed in this task. The existing runtime rows are observations already present in saved logs only.

## Additive deliverables and limitations

`SCRIPTS/CAPTURE_VALIDATOR.py` is self-contained for direct invocation from any working directory, uses stdlib plus the adjacent phase12 parser, and checks saved binary decode parity and provenance association totals. The parser now adds its own script directory to `sys.path` for direct invocation portability.

The native source/build notes are in [`PCU_READONLY_DIAGNOSTICS/`](PCU_READONLY_DIAGNOSTICS/README.md). The harness is bounded, read-only DDE `XTYP_REQUEST`/`CF_TEXT` only. Linux lacks Win32 DDE headers/libraries; therefore neither a Windows compile nor live execution is claimed. Its exact constraints and unsupported behaviors are documented in that README.
