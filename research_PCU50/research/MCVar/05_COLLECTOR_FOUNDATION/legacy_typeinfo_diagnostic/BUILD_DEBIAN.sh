#!/bin/sh
set -eu
cd "$(dirname "$0")"
CC=${CC:-i686-w64-mingw32-gcc}
export SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-0}
command -v "$CC" >/dev/null 2>&1 || { echo "missing compiler: $CC" >&2; exit 1; }
"$CC" -std=c99 -Wall -Wextra -Werror -O2 -municode stage15_diag.c -o stage15_diag.exe -loleaut32 -lole32 -ladvapi32
file stage15_diag.exe
