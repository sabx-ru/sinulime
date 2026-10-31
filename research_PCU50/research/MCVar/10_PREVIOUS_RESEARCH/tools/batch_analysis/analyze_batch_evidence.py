#!/usr/bin/env python3
"""Analyze saved MCVar batch evidence and emit a conservative benchmark report."""
from __future__ import annotations
import argparse, json, re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT.parent
EV = ROOT / "phase12/BATCHING_EVIDENCE.json"
CORPUS = ROOT / "phase11/REAL_INPUT_CORPUS/cases.json"
SIZES = (1, 2, 5, 10, 20, 40)


def invocation_latencies() -> dict[int, list[int]]:
    """Read logged whole-ReadVar elapsed_ms values, without inferring item timings."""
    cases = json.loads(CORPUS.read_text(encoding="utf-8"))["cases"]
    result = defaultdict(list)
    for case in cases:
        if case.get("kind") != "MC":
            continue
        log = PROJECT / case["log"]
        if not log.exists():
            continue
        text = log.read_text(encoding="utf-8", errors="replace")
        for match in re.finditer(r"ROUND=(\d+) elapsed_ms=(\d+)", text):
            round_no, elapsed = int(match.group(1)), int(match.group(2))
            rounds = [r for r in case.get("mc_rounds", []) if r.get("round") == round_no]
            if rounds:
                result[rounds[0]["requested"]].append(elapsed)
    return result


def load_rounds(path: Path = EV):
    evidence = json.loads(path.read_text(encoding="utf-8"))
    rounds = []
    for step in evidence["steps"].values():
        for round_ in step.get("mc_rounds", []):
            row = dict(round_)
            row["name"] = step["name"]
            rounds.append(row)
    return evidence, rounds


def analyze(path: Path = EV) -> dict:
    evidence, rounds = load_rounds(path)
    timings = invocation_latencies()
    by_size = defaultdict(list)
    for row in rounds:
        by_size[row["requested_elements"]].append(row)
    summary = {}
    for size in SIZES:
        rows = by_size[size]
        elapsed = timings.get(size, [])
        summary[str(size)] = {
            "invocations": len(rows),
            "processed_elements": sum(r["processed_elements"] for r in rows),
            "hresults": dict(Counter(r["hresult"] for r in rows)),
            "cache_values": sorted({r["cache"] for r in rows}),
            "item_error_invocations": sum(bool(r["element_error_slots"]) for r in rows),
            "invocation_latency_ms": {"status": "measured", "samples": elapsed, "source": "saved mcvar_multiread logs ROUND elapsed_ms"} if elapsed else {"status": "unavailable", "reason": "no matching saved elapsed_ms record"},
            "per_item_latency_ms": {"status": "unavailable", "reason": "logs do not timestamp individual item completion"},
        }
    return {
        "schema_version": 1,
        "source": "research/phase12/BATCHING_EVIDENCE.json and saved real-test corpus",
        "live_pcu_execution": False,
        "transaction_count": {"status": "unavailable", "reason": "saved captures correlate counter transitions but do not observe backend boundaries"},
        "sizes": summary,
        "findings": {
            "order": "preserved by request index and result array position in saved logs; no reorder claim beyond observed cases",
            "duplicates": "duplicate-input cases are present and returned per position; no deduplication claim",
            "lower_bounds": "sizes 1, 5, and 20 have explicit LOWERBOUND cases; these are lower-bound experiment labels, not transaction counts",
            "errors": "mixed item errors coexist with outer S_OK; all-bad cases have outer 0x80020009; unsupported array-variant has 0x80070057 item error",
            "cache": "saved runs vary cache 0/1/2, including size 1 and 20; causal cache or latency effect is not established",
            "size_40": "not present in saved MCVar rounds; requires future bounded run (two chunks of 20 in planner)",
        },
        "backend_transaction_counts_claimed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = analyze()
    text = json.dumps(result, indent=2) + "\n"
    if args.output: args.output.write_text(text, encoding="utf-8")
    else: print(text, end="")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
