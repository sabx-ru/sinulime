#!/usr/bin/env python3
"""Offline structural decoder for preserved NCDDE binary captures."""
from __future__ import annotations

import json
import struct
from pathlib import Path

# Support direct invocation from any working directory without installing a package.
if __package__ in (None, ""):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))

MARKER = bytes.fromhex("f9 f8 f7 f6")


def parse_binary(data: bytes) -> dict:
    if len(data) < 20:
        raise ValueError(f"binary response too short: {len(data)}")
    if struct.unpack_from("<H", data, 0)[0] != 20:
        raise ValueError("unexpected declared header size")
    if struct.unpack_from("<H", data, 2)[0] != 1:
        raise ValueError("unexpected protocol version")
    if data[16:20] != MARKER:
        raise ValueError("missing marker at offset 16")

    value_type = data[6]
    subtype = data[4]
    sequence = data[7]
    payload_size = struct.unpack_from("<I", data, 12)[0]
    payload = data[20:]
    if payload_size != len(payload):
        raise ValueError(f"payload size {payload_size} != actual {len(payload)}")

    result = {
        "header_size": 20,
        "version": 1,
        "value_type": value_type,
        "subtype": subtype,
        "sequence": sequence,
        "payload_size": payload_size,
        "marker": MARKER.hex(),
        "payload_hex": payload.hex(),
    }
    kind_code = (data[4], data[6])
    if kind_code[0] == 1 and kind_code[1] in (2, 3) and len(payload) == 4:
        result.update(kind="integer", value=struct.unpack("<i", payload)[0])
    elif kind_code == (2, 5) and len(payload) == 8:
        result.update(kind="double", value=struct.unpack("<d", payload)[0])
    elif kind_code == (100, 6) and len(payload) == 8:
        result.update(kind="BCD_clock", all_nibbles_decimal=all((b >> 4) <= 9 and (b & 15) <= 9 for b in payload))
    elif kind_code == (100, 6):
        result.update(kind="string", text=payload.split(b"\x00", 1)[0].decode("latin-1"))
    else:
        result.update(kind="unknown", value=None)
    return result


def parse_text(data: bytes) -> dict:
    if not data or data[-1] != 0:
        raise ValueError("CF_TEXT capture must end in NUL")
    return {"format": "CF_TEXT", "byte_length": len(data), "raw_hex": data.hex(), "text": data[:-1].decode("latin-1")}


def corpus_report(corpus: Path) -> dict:
    meta = json.loads((corpus / "provenance.json").read_text())
    binary = []
    text = []
    for item in meta["associations"]:
        path = corpus / item["capture"]
        content = path.read_bytes()
        if item["format"] == "binary":
            parsed = parse_binary(content)
            binary.append({"capture": item["capture"], "item": item["item"], **parsed})
        elif item["format"] == "text":
            text.append({"capture": item["capture"], "item": item["item"], **parse_text(content)})
    return {"binary_count": len(binary), "text_count": len(text), "binary": binary, "text": text}


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    corpus = root / "research/phase11/REAL_INPUT_CORPUS"
    report = corpus_report(corpus)
    print(json.dumps({k: v for k, v in report.items() if k.endswith("_count")}, indent=2))
