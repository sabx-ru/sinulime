# Siemens 840D Powerline — NCDDE read-only research

An independently developed, **read-only diagnostic client** and reproducible research notes for reading selected SINUMERIK 840D Powerline machine data through the existing **NCDDE** service on an older **PCU50 / Windows XP (32-bit)** installation.

**Status (2026-11-11):** the client was built externally on Debian and executed successfully on a real PCU50. Eight one-shot DDE requests returned structurally valid binary responses, including selected General MD, Channel MD, Axis MD, and one Drive MD. **This does not establish universal MD access, a reliable X/Y axis mapping, or safe behavior for every machine.**

This is a research/diagnostic tool, **not** a replacement for HMI Advanced, a production data-collection service, or a control application. Not affiliated with or endorsed by Siemens.

[Русский README](README.ru.md) · [Field results](docs/field-tests.md) · [Protocol observations](docs/protocol.md) · [Reverse-engineering findings](docs/static-research.md) · [Research history](docs/research-timeline.md) · [Safety](docs/safety.md)

## What is actually demonstrated?

| Read category | Observed NCDDE item | Result on one PCU50 |
|---|---|---|
| System baseline | `/Nck/Configuration/numGlobMachAxes` | `2` |
| General MD / TEA | `/acc/nc_tea/$MN_SYSCLOCK_CYCLE_TIME` | `0.004` |
| Channel MD / TEA | `/acc/ch_tea/$MC_CHAN_NAME` | `CHAN1` |
| Axis MD / TEA | `/acc/ax_tea/$MA_CTRLOUT_MODULE_NR` | `1` |
| General MD / PRE | `/acc/nc_pre/$MN_SYSCLOCK_CYCLE_TIME` | `0.004` |
| Channel MD / PRE | `/acc/ch_pre/$MC_RESET_MODE_MASK` | `0` |
| Axis MD / PRE | `/acc/ax_pre/$MA_AX_MOTION_DIR` | `1` |
| Drive MD / PRE | `/acc/vs_pre/$MD_MOTOR_NOMINAL_CURRENT` | `17.600000381469727` |

These are **observations from one installation**, not standard values for every SINUMERIK machine. The drive value is **nominal motor current**, not live current draw; its physical-axis binding has not been verified. See [field-tests.md](docs/field-tests.md) for the complete evidence and limits.

## How it works

```text
  XP diagnostic CLI (this repository)
      |
      | DDEML: DdeConnect + one XTYP_REQUEST
      | service = ncdde, topic = machineswitch
      | format = ncddeBinary
      v
  Siemens NCDDE server (already installed on PCU50)
      |
      | LINK/NSK-mapped NCK or drive variable
      | internal route not traced in this experiment
      v
  Binary response -> HEX log + cautious candidate decoder
```

The test client does **not** use MCVar, call HMI Advanced UI controls, create NCDDE mappings, install a service, or write to a controller. The relationship of HMI's `ibmd.exe`/`ibdrv.exe`, `sllist.dll`, `slacx.dll`, `dctl.ocx`, MCVar, and NCDDE remains a separate reverse-engineering question; see [static-research.md](docs/static-research.md).

## Build on Debian

Install a 32-bit MinGW-w64 toolchain:

```bash
sudo apt update
sudo apt install gcc-mingw-w64-i686-win32 binutils-mingw-w64-i686 file
./BUILD_DEBIAN.sh
```

The build script produces:

```text
windows/bin/ncdde_md_probe.exe
windows/bin/pe_imports.txt
```

The executable is built for x86 with PE subsystem **5.01** and a check for several known post-XP imports. This check is **not a full compatibility guarantee**. A previous build was successfully run on the test PCU50; newly built versions should still be verified. See [build-and-run.md](docs/build-and-run.md).

## Run on the PCU50

**Only on an authorized, safely stopped machine with a verified backup and a responsible operator present.** Previous drive alarms were observed after an older DDE experiment; causality is not established. Do not assume that a read-only application cannot trigger server-side effects.

1. Copy the complete `windows/` directory (including the built EXE, `sets/` and `.cmd` files) to the XP PCU50.
2. Confirm the original HMI/NCDDE environment is operating normally, with no axis movement or pending fault. Start with `RUN_00_BASELINE.cmd`.
3. If the baseline works, run **one selected** non-drive test at a time, e.g. `RUN_01_MD_GENERAL_TEA.cmd`. Review the output.
4. Find the individual plain-text result under `windows/logs/`.
5. **Do not start** `RUN_08_MD_DRIVE_MANUAL.cmd` or custom drive items merely because other requests passed. PLC/custom items need separately validated addresses.

Each invocation uses one item, one DDE `XTYP_REQUEST`, no automatic retries and no background monitoring. `RUN_00_BASELINE_TEXT.cmd` attempts `CF_TEXT`, but this mode was **not** included in the 2026-11-11 field validation.

## Offline verification (no PCU required)

Python 3 (standard library only):

```bash
python3 tools/verify_frames.py
python3 -m unittest discover -s tests -v
```

This validates eight [anonymized captured response frames](fixtures/observed_frames.json), their framing, type/payload interpretation for the **observed cases**, and equality of the two General MD payloads.

If you have your **private** original capture ZIP, you can check its log frames without uploading them:

```bash
python3 tools/verify_frames.py --log-zip /path/to/windows.zip
```

The static analysis scripts in `tools/` also work offline but require **your own lawfully obtained original** Siemens PE files or `.NSK` data; none are distributed here. See [reproduce.md](docs/reproduce.md).

## Repository layout

```text
src/                      Native Win32 DDEML one-shot client (C)
BUILD_DEBIAN.sh            Debian -> Windows XP cross-compilation
windows/RUN_*.cmd         Individual test launchers
windows/sets/*.txt        One exact DDE item per test
windows/bin/              Output only (EXEs excluded from Git)
windows/logs/             Local logs only (excluded from Git)
fixtures/                 Anonymized observed binary frames
tools/verify_frames.py       Offline capture verification
tools/verify_binary_edges.py Optional PE callsite verification
tools/reproduce_map.py       Optional .NSK/map cross-check
tests/                       Standard-library unit tests
docs/                        Protocol, findings, limits and safety
```

## What is **not** proved

- Arbitrary MD lookup by number without a predefined active `LINK`/NSK mapping.
- The second axis's indexing and a reliable X/Y-to-physical-drive mapping.
- PLC bit reads by this particular test client.
- Live motor current or scaling for servo drives.
- Freshness of each reading versus server cache, and timing of an actual NCU transaction.
- A complete runtime `ibmd.exe` / `ibdrv.exe` → `sllist.dll` → `slacx.dll` → NCDDE → HMI value path.
- Harmlessness of drive queries on arbitrary production hardware.

The deliberately limited scope is detailed in the [evidence ledger](docs/evidence-ledger.md).

## Legal / publication note

Only original research scripts, the independent diagnostic client, and a small curated capture sample are included. **No Siemens PE files, full decompilations, HMI disk images, full `.NSK` catalogs, or unredacted PCU logs** are part of this public package. You must have rights to publish any additional material you contribute. Siemens and SINUMERIK are trademarks of their respective owners; this project is independent.

See [NOTICE.md](NOTICE.md) and the [publication checklist](docs/publication-checklist.md). Code is offered under the [MIT license](LICENSE), without warranty.
