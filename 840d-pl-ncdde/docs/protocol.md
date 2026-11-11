# Observed NCDDE protocol subset

This page describes a **measured subset** of the binary reply format. It is **not** a complete Siemens NCDDE protocol specification and does not describe how NCDDE internally accesses NCU, PLC or drives.

## One-shot DDEML request

The Windows XP client follows:

```text
DdeInitializeA(APPCMD_CLIENTONLY)
  DdeCreateStringHandleA("ncdde")
  DdeCreateStringHandleA("machineswitch")
  DdeCreateStringHandleA("/acc/nc_tea/$MN_SYSCLOCK_CYCLE_TIME")
  DdeConnect(service, topic)
  RegisterClipboardFormatA("ncddeBinary")
  DdeClientTransaction(..., XTYP_REQUEST, format, timeout)
  DdeGetData(...)
  DdeFreeDataHandle / DdeDisconnect / DdeUninitialize
```

This is the observed client operation, not evidence that `ibmd.exe` itself uses the same call sequence. `XTYP_POKE`, `XTYP_EXECUTE` and `XTYP_ADVSTART` are not implemented in the probe.

## Binary frame layout observed in eight replies

All eight frames matched the following 20-byte structure and marker:

| Byte offset | Length | Interpretation in recorded replies |
|---:|---:|---|
| `0` | 2 | Little-endian `header_len` = `20` |
| `2` | 2 | Little-endian `version` = `1` |
| `4` | 2 | Little-endian `value_class` |
| `6` | 1 | `value_type` |
| `7` | 1 | `sequence-like` byte, observed `A1..A8` in time order |
| `8` | 4 | Little-endian field (`count` in offline parser); was `1` in recorded cases |
| `12` | 4 | Little-endian payload length |
| `16` | 4 | Marker `F9 F8 F7 F6` |
| `20` | variable | Payload, exact length as in offset 12 |

The names of some metadata fields are tentative. In particular, the changing byte at offset 7 is **consistent** with a reply sequence counter, but cannot establish the number of underlying NCU reads. The count field's meaning for arrays has not been validated.

## Observed payload pairs

`(value_class, value_type)` must be interpreted **together with item and payload length**. The following combinations were checked against one test corpus:

| Pair | Example item | Payload bytes | Observed meaning |
|---|---|---|---|
| `(1,2)` | `/Nck/Configuration/numGlobMachAxes` | 4 | signed little-endian int32 (`2`) |
| `(1,3)` | `/acc/ch_pre/$MC_RESET_MODE_MASK` | 4 | signed little-endian int32 (`0`) |
| `(1,8)` | `/acc/ax_tea/$MA_CTRLOUT_MODULE_NR` | 4 | signed little-endian int32 (`1`) |
| `(2,5)` | `/acc/nc_tea/$MN_SYSCLOCK_CYCLE_TIME` | 8 | IEEE754 little-endian float64 (`0.004`) |
| `(2,14)` | `/acc/vs_pre/$MD_MOTOR_NOMINAL_CURRENT` | 8 | IEEE754 little-endian float64 (`17.600000381469727`) |
| `(100,6)` | `/acc/ch_tea/$MC_CHAN_NAME` | 16 | NUL-padded ASCII (`CHAN1`) |

This is **not** a general rule for all array types, string encodings, numeric widths, indexing, or variable categories. The original C probe prints generic numeric candidates even for strings; those are **not decoded values**.

## Example: General MD (recorded sample)

Item:

```text
/acc/nc_tea/$MN_SYSCLOCK_CYCLE_TIME
```

Complete response (HEX):

```text
14 00 01 00 02 00 05 A2 01 00 00 00 08 00 00 00
F9 F8 F7 F6 FC A9 F1 D2 4D 62 70 3F
```

The payload `FC A9 F1 D2 4D 62 70 3F` represents the float64 value `0.004`. The sample's `A2` is not a fixed constant across responses.

A second request using `/acc/nc_pre/$MN_SYSCLOCK_CYCLE_TIME` produced the same eight payload bytes. The complete binary frames differed only at the sequence-like header byte.

## Selector names and `.NSK` descriptors

The tested `/acc/*_tea/` and `/acc/*_pre/` items correspond to `LINK(...)` entries in locally held Siemens configuration files. A `LINK` binds a symbolic item to an internal descriptor. Some `*_tea` names were derived via `Slacx_NcMap::CreateNskFile`, but the existence of a `LINK` **does not guarantee** it is loaded or readable on every machine.

Do **not** assume `*_tea` and `*_pre` are interchangeable. For example, archived entries for `$MC_RESET_MODE_MASK` differ in their `/NC` type token (`10` in `ch_tea`, `3` in `ch_pre`). The field test covered only `ch_pre` for that specific MD.

## Failure handling and caveats

- A DDE connect success is not a successful read.
- A data handle is not semantic proof of a correct MD type, unit, physical axis or freshness.
- A frame can pass header checks while containing a wrong interpretation.
- Very short elapsed times can reflect caching; the test cannot distinguish cache hits from fresh NCU transactions.
- `ncddeBinary` reply format is vendor-specific; the portable Python decoder intentionally handles only the six observed pairs above.

Run `python3 tools/verify_frames.py` to reproduce the checks offline.
