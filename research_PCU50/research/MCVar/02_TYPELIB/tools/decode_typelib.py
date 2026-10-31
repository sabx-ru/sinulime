#!/usr/bin/env python3
"""Decode preserved MSFT TypeLib resources with pycomtypelib."""
import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

DEFAULTS = {
    "old": Path(os.environ.get("MCVAR_OLD_TYPELIB", "/root/PL/research/MCVar/api/resources/old_TYPELIB_1_1033.bin")),
    "new": Path(os.environ.get("MCVAR_NEW_TYPELIB", "/root/PL/research/MCVar/api/resources/new_TYPELIB_1_1033.bin")),
}


def decode(path):
    path = Path(path)
    raw = path.read_bytes()
    cli = Path(__file__).parent / ".venv/bin/pycomtypelib"
    proc = subprocess.run([str(cli), "dump", "--json", str(path)], check=True, capture_output=True, text=True)
    model = json.loads(proc.stdout)
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size": len(raw),
            "library": model, "typeinfo_count": len(model["typeinfos"])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", type=Path, default=DEFAULTS["old"])
    ap.add_argument("--new", type=Path, default=DEFAULTS["new"])
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    result = {name: decode(path) for name, path in (("old", args.old), ("new", args.new))}
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text)
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
