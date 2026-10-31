# Batch Reading Report

## Saved evidence

The deterministic analyzer reads preserved Phase 12 evidence and logged whole-call `elapsed_ms` values. It does not observe backend transactions or per-item completion.

| requested size | saved invocations | whole-call samples | per-item latency | backend count |
|---:|---:|---:|---|---|
| 1 | 18 | 18 | unavailable | unavailable |
| 2 | 1 | 1 | unavailable | unavailable |
| 5 | 17 | 17 | unavailable | unavailable |
| 10 | 1 | 1 | unavailable | unavailable |
| 20 | 23 | 23 | unavailable | unavailable |
| 40 | 0 | 0 | unavailable | unavailable |

Representative saved whole-call latencies include size 1 samples 0-50 ms, size 5 samples 20-50 ms, size 10 one 50 ms sample and size 20 samples 70-151 ms. These are not a controlled benchmark: sample counts, cache composition, machine state and test timing are not balanced.

## Behavior

Saved tests cover order, duplicates, lower-bound labels, mixed valid/invalid slots, rejected VARIANT-array shapes and CacheDevice values 0/1/2. Results preserve tested positions. Mixed per-item errors can coexist with outer S_OK. No backend transaction count or atomic snapshot is established.

## Implementation recommendation

Use the bounded planner in `scripts/mcvar_batch_planner.py`: one call for at most the tested bound of 20; chunk larger configured sets into calls of at most 20; preserve order and duplicates. This is an SDK policy, not a proven Siemens maximum or transport model. Size 40 remains untested; its offline plan is two 20-item calls.

## Benchmark package

- `scripts/analyze_batch_evidence.py`: saved-log analyzer.
- `scripts/benchmark_schema.py`: measured/unavailable/not_measured result schema.
- `results/BENCHMARK_RESULTS.json`: generated machine-readable output.
- `scripts/tests/test_batch_package.py`: 7 offline tests.

A real performance recommendation requires a controlled authorized Windows/PCU run comparing singles, one-call and chunks with warm-up, sample count, p50/p95/p99, CPU/memory and failure/quality metrics. No such live benchmark was executed.
