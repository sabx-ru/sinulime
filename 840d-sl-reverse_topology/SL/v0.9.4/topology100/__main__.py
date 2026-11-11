"""Offline v1.0.0 evidence report command."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evidence import build_evidence, write_evidence


def main() -> int:
    parser = argparse.ArgumentParser(description="SINUMERIK topology evidence v1.0.0")
    parser.add_argument("--reads", required=True)
    parser.add_argument("--sdb")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    doc = build_evidence(args.reads, args.sdb)
    write_evidence(doc, args.out)
    print(json.dumps(doc["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
