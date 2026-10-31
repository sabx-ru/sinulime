#!/usr/bin/env python3
"""Self-contained offline corpus validation; performs no PCU communication."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PHASE12 = HERE.parent
ROOT = PHASE12.parents[1]
# Direct execution works from arbitrary cwd and with a standalone copied folder.
sys.path.insert(0, str(PHASE12 / "scripts"))
import ncdde_capture_parser as capture_parser


def validate(corpus: Path) -> dict:
    report = capture_parser.corpus_report(corpus)
    decoded_path = corpus / "decoded_binary.json"
    decoded = json.loads(decoded_path.read_text(encoding="utf-8"))
    errors = []
    if report["binary_count"] != len(decoded):
        errors.append(f"binary count {report['binary_count']} != decoded count {len(decoded)}")
    for i, (actual, expected) in enumerate(zip(report["binary"], decoded)):
        for key in ("payload_hex", "sequence", "kind"):
            if actual.get(key) != expected.get(key):
                errors.append(f"binary[{i}] {key} mismatch")
    meta = json.loads((corpus / "provenance.json").read_text(encoding="utf-8"))
    associations = meta["associations"]
    if len(associations) != report["binary_count"] + report["text_count"]:
        errors.append("association count does not match parsed capture count")
    return {
        "source": "saved phase11 corpus only; no live PCU execution",
        "corpus": str(corpus.resolve()),
        "binary_count": report["binary_count"],
        "text_count": report["text_count"],
        "decoded_binary_count": len(decoded),
        "association_count": len(associations),
        "errors": errors,
        "valid": not errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=ROOT / "research/phase11/REAL_INPUT_CORPUS")
    args = parser.parse_args()
    result = validate(args.corpus)
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
