#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
CC="${CC:-i686-w64-mingw32-gcc-win32}"
OBJDUMP="${OBJDUMP:-i686-w64-mingw32-objdump}"
command -v "$CC" >/dev/null || { echo "Install: sudo apt install gcc-mingw-w64-i686-win32 binutils-mingw-w64-i686" >&2; exit 1; }
command -v "$OBJDUMP" >/dev/null || { echo "Missing: $OBJDUMP" >&2; exit 1; }
mkdir -p windows/bin windows/logs
"$CC" -std=gnu99 -O2 -Wall -Wextra -Wno-unused-parameter \
  -DWINVER=0x0501 -D_WIN32_WINNT=0x0501 \
  -static -static-libgcc \
  -Wl,--major-subsystem-version,5,--minor-subsystem-version,1 \
  -o windows/bin/ncdde_md_probe.exe src/ncdde_md_probe.c -luser32
"$OBJDUMP" -p windows/bin/ncdde_md_probe.exe > windows/bin/pe_imports.txt
if grep -Eiq 'DLL Name: (api-ms-win|KERNELBASE\.dll)|\b(GetThreadId|GetTickCount64|InitializeCriticalSectionEx|CancelIoEx|SetThreadDescription)\b' windows/bin/pe_imports.txt; then
  echo 'ERROR: Found suspicious XP-incompatible dependency; inspect windows/bin/pe_imports.txt' >&2
  exit 1
fi
file windows/bin/ncdde_md_probe.exe
sha256sum windows/bin/ncdde_md_probe.exe
printf 'Built: %s/windows/bin/ncdde_md_probe.exe\n' "$PWD"
