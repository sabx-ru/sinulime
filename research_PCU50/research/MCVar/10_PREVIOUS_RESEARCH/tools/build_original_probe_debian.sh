#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
OUT="$ROOT/PCU_DIAGNOSTICS/bin/mcvar_typeinfo_probe.exe"
if ! command -v i686-w64-mingw32-g++ >/dev/null 2>&1; then
  echo "i686-w64-mingw32-g++ is required for Debian cross-build" >&2
  exit 2
fi
i686-w64-mingw32-g++ -std=c++17 -Wall -Wextra -O2 "$ROOT/PCU_DIAGNOSTICS/src/mcvar_typeinfo_probe.cpp" -o "$OUT" -loleaut32 -lole32
file "$OUT"
