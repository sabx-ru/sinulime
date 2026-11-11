# Build on Debian; run on Windows XP PCU50

## Requirements

- Development host: Debian Linux and 32-bit MinGW-w64 (`i686-w64-mingw32-gcc-win32`, `i686-w64-mingw32-objdump`).
- Target: PCU50 on an authorized SINUMERIK 840D Powerline installation, Windows XP x86, where the **existing** NCDDE/HMI software is functioning.
- Access to the PCU only under a site-approved safe-state procedure. No control motion, no changes to the Siemens application configuration.
- `DdeConnect` must be able to reach the local DDE service. This application does not start a service.

## Cross-compile

```bash
sudo apt update
sudo apt install gcc-mingw-w64-i686-win32 binutils-mingw-w64-i686 file
./BUILD_DEBIAN.sh
```

`BUILD_DEBIAN.sh` compiles `src/ncdde_md_probe.c` using `-DWINVER=0x0501`, `-D_WIN32_WINNT=0x0501`, 32-bit Windows target, static runtime options, and subsystem version **5.01**. The script creates `windows/bin/ncdde_md_probe.exe` and emits `windows/bin/pe_imports.txt`, then checks for a few known incompatible entry points (including `GetThreadId`).

**Limits:** those flags and checks do not prove XP compatibility for all future compilers or dependencies. The observed PCU field run establishes that one compiled version ran; rebuilds should be tested separately.

## Deploy

Copy the complete `windows/` directory, not only the EXE. For example:

```text
C:\NCDDE_TEST\
    bin\ncdde_md_probe.exe
    sets\*.txt
    logs\
    RUN_TEST.cmd
    RUN_00_BASELINE.cmd
    RUN_01_MD_GENERAL_TEA.cmd
    ...
```

No Siemens DLL, service registration, registry edit or `.NSK` generation is part of the deployment.

## Run the tests, one at a time

| CMD | Category | Selector location | Tested on 2026-11-11? |
|---|---|---|---|
| `RUN_00_BASELINE.cmd` | NCK configuration | `sets/00_BASELINE.txt` | Yes |
| `RUN_00_BASELINE_TEXT.cmd` | Same item with CF_TEXT | `sets/00_BASELINE.txt` | **No** |
| `RUN_01_MD_GENERAL_TEA.cmd` | General / TEA | `sets/01_MD_GENERAL_TEA.txt` | Yes |
| `RUN_02_MD_CHANNEL_TEA.cmd` | Channel / TEA | `sets/02_MD_CHANNEL_TEA.txt` | Yes |
| `RUN_03_MD_AXIS_TEA.cmd` | Axis / TEA | `sets/03_MD_AXIS_TEA.txt` | Yes |
| `RUN_04_MD_GENERAL_PRE.cmd` | General / PRE | `sets/04_MD_GENERAL_PRE.txt` | Yes |
| `RUN_05_MD_CHANNEL_PRE.cmd` | Channel / PRE | `sets/05_MD_CHANNEL_PRE.txt` | Yes |
| `RUN_06_MD_AXIS_PRE.cmd` | Axis / PRE | `sets/06_MD_AXIS_PRE.txt` | Yes |
| `RUN_07_PLC_MANUAL.cmd` | PLC / manually reviewed item | `sets/07_PLC_MANUAL.txt` | **No** |
| `RUN_08_MD_DRIVE_MANUAL.cmd` | Drive / PRE, requires confirmation | `sets/08_MD_DRIVE_PRE.txt` | Yes; **do not repeat casually** |
| `RUN_09_CUSTOM.cmd` | Operator-approved exact address | `sets/09_CUSTOM.txt` | **No** |

1. Have the machine authorized and secured in a no-motion state. Review [safety.md](safety.md).
2. Run **only** `RUN_00_BASELINE.cmd` first; confirm a normal value and NCDDE response.
3. Select a known General, Channel or Axis item if additional tests are authorized.
4. Stop if there is a new warning, alarm or unexpected operation. Document controller state and provide the capture to the responsible technician.
5. Do not infer that a returned axis MD is the second physical axis, or that a drive value is real-time current.

The manual PLC selector deliberately contains only a comment and therefore fails closed unless the operator provides one reviewed exact address. Each `sets/*.txt` accepts exactly **one** non-commented, leading-`/` item.

## Command invocation

All launchers ultimately use this structure:

```bat
bin\ncdde_md_probe.exe --items=sets\01_MD_GENERAL_TEA.txt --label=01_MD_GENERAL_TEA --topic=machineswitch --format=binary --timeout=3000
```

- Service: hard-coded `ncdde`.
- Topic: default `machineswitch`; CLI allows a topic override (unverified on other topics).
- Format: `binary` registers `ncddeBinary`; `text` uses standard `CF_TEXT` (untested in these eight logs).
- Request timeout: default `3000` ms, accepted range `100..5000` ms.
- One request per process; no retries/subscriptions and no write transaction.
- Individual log path: `logs\LABEL_YYYYMMDD_HHMMSS_PID.txt`; stdout mirrors this file.

## Output interpretation

A positive `CONNECTED=YES` means the client connected to a DDE conversation, **not** that the requested MD was read. The successful recorded cases also have `RESULT=DATA_HANDLE`, nonzero returned length, `EXIT=0`, and a verified 20-byte binary header/payload. `CANDIDATE_INT32` and `CANDIDATE_DOUBLE` printed by the old C client are deliberately generic **candidates**, not type-safe results for every selector. Use the offline verifier and the matching original `LINK` descriptor when available.

## Returning results for research

Prefer a small redacted bundle containing selected `logs/*.txt` and test identifiers, plus an explicit note of whether alarms appeared before/after. Before sending or publishing, remove names, customer information, disk paths, network data and machine identification.
