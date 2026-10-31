#!/usr/bin/env python3
"""Offline packet invariants for captured binary DDE responses."""
from collections import Counter
from pathlib import Path
import argparse
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
CAPTURES = ROOT / "real_tests" / "logs" / "02_RUN_RESEARCH"
HEADER_LEN = 0x14
MARKER = bytes.fromhex("f9 f8 f7 f6")


def inspect(path: Path):
    data = path.read_bytes()
    if len(data) < HEADER_LEN:
        raise ValueError(f"{path}: shorter than {HEADER_LEN}-byte header")
    declared_header, field2, field4, field6 = struct.unpack_from("<HHHH", data)
    payload_length = struct.unpack_from("<I", data, 12)[0]
    if declared_header != HEADER_LEN:
        raise ValueError(f"{path}: header length {declared_header:#x}")
    if data[16:20] != MARKER:
        raise ValueError(f"{path}: marker mismatch {data[16:20].hex()}")
    if payload_length != len(data) - HEADER_LEN:
        raise ValueError(
            f"{path}: stored payload length {payload_length} != actual {len(data)-HEADER_LEN}"
        )
    return len(data), field2, field4, field6, payload_length


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--captures", type=Path, default=CAPTURES)
    args = parser.parse_args()
    paths = sorted(set(args.captures.glob("*binary.bin")) | set(args.captures.glob("*binary.hex")))
    if not paths:
        print(f"No binary captures found under {args.captures}", file=sys.stderr)
        return 2
    distributions = Counter()
    failures = []
    for path in paths:
        try:
            raw = path.read_bytes()
            if path.suffix == ".hex":
                tokens = path.read_text(encoding="ascii").split()
                if not tokens or any(len(token) != 2 for token in tokens):
                    raise ValueError(f"{path}: malformed whitespace-separated hex")
                raw = bytes(int(token, 16) for token in tokens)
            data = raw
            if len(data) < HEADER_LEN:
                raise ValueError(f"{path}: shorter than {HEADER_LEN}-byte header")
            declared_header, field2, field4, field6 = struct.unpack_from("<HHHH", data)
            payload_length = struct.unpack_from("<I", data, 12)[0]
            if declared_header != HEADER_LEN:
                raise ValueError(f"{path}: header length {declared_header:#x}")
            if data[16:20] != MARKER:
                raise ValueError(f"{path}: marker mismatch {data[16:20].hex()}")
            if payload_length != len(data) - HEADER_LEN:
                raise ValueError(f"{path}: stored payload length {payload_length} != actual {len(data)-HEADER_LEN}")
            total = len(data)
            distributions[(total, field2, field4, payload_length)] += 1
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            failures.append(str(exc))
    print(f"captures={len(paths)} valid={len(paths)-len(failures)} invalid={len(failures)}")
    for (total, f2, f4, payload), count in sorted(distributions.items()):
        print(f"total={total} header=0x14 field2={f2} field4={f4} payload={payload}: {count}")
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
