# Reproduction guide and provenance

## A. Reproduce the public field-frame checks (no equipment)

From repository root:

```bash
python3 tools/verify_frames.py
python3 -m unittest discover -s tests -v
```

Expected result for the included anonymized fixture: **8 validated frames**, **4 passing unit tests**. The script verifies framing and payload interpretation only for the observed type/length pairs and checks that the two General MD payloads match.

`fixtures/observed_frames.json` is the complete set of eight captured frame bytes, plus item strings and expected decoded values, with filenames, PID and precise timestamps removed. It is *real recorded data*, not synthetic output, but it cannot by itself prove what was occurring physically on the machine.

## B. Recheck private log ZIP offline

If you have the original operator-owned capture:

```bash
python3 tools/verify_frames.py --log-zip /path/to/windows.zip
```

This does not upload, send or modify the ZIP; it only parses it locally. The original offline audit also matched all eight items against corresponding original Siemens `.NSK` declarations; that additional step is omitted from the public checker because proprietary configurations and full machine directories are excluded.

Expected SHA256 of the exact private `windows.zip` originally reviewed:

```text
d18f78c2f538c43ef109b7058af9494fe391e418549518ae3e986fb7714e37e1
```

A different archive hash may still be valid but cannot be claimed to be the same original evidence without comparison.

## C. Reproduce selected static PE cross-checks

Obtain the **same exact versions** of original `ibdrv.exe`, `sllist.dll`, `slacx.dll`, and `dctl.ocx` from a lawfully held local PCU backup. Do not publish them. Then:

```bash
python3 tools/verify_binary_edges.py --bin-dir /path/to/original/pe-files
```

All addresses and expected calls in this script are specific to the recorded versions and will likely differ on other builds.

## D. Reproduce the saved `.NSK` map comparison

With locally held original inputs:

```bash
python3 tools/reproduce_map.py \
  --slacx /path/to/slacx.dll \
  --sllist /path/to/sllist.dll \
  --ibdrv /path/to/ibdrv.exe \
  --nsk-dir /path/to/nsk \
  --out /tmp/840d-verify-nsk
```

This parser is intentionally strict and targets the 2026-11-10 historical `nc_tea.nsk`, `ch_tea.nsk`, and `ax_tea.nsk` layout. It writes local TSV/JSON analysis files; these results should **not** be committed without licensing and privacy review. On a different PCU release or user-modified `.NSK`, parser failure need not indicate incorrect software behavior.

## E. Build check

```bash
bash -n BUILD_DEBIAN.sh
./BUILD_DEBIAN.sh
```

The `BUILD_DEBIAN.sh` step needs the MinGW-w64 packages. Only source code, not a prebuilt executable, ships with the public repository. For current target packages, consult your Debian installation; do not claim that a successful Linux build proves safe deployment on an industrial controller.

## Evidence provenance registry

| Artifact | Included publicly? | Purpose |
|---|---|---|
| `src/ncdde_md_probe.c` | Yes | client implementation |
| Debian build + XP `.cmd` launchers | Yes | repeatable build and single-item tests |
| Eight anonymized response frames | Yes | byte-level public regression fixture |
| `windows.zip` real PCU capture | **No** | local original field logs |
| Siemens `.NSK`, PE and OCX | **No** | local mapping/binary verification |
| HMI Advanced disk images and ProcMon/API Monitor captures | **No** | private contextual evidence |
| Decompiled original PE listings | **No** | excluded third-party content |
