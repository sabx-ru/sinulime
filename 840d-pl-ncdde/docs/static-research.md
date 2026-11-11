# Static reverse-engineering findings (2026-11-10)

**Scope:** selected original PE files for HMI Advanced and independent NCDDE-related modules. Findings were obtained from locally held files. No Siemens executable, decompiled function body, full listing, or proprietary config catalog is distributed in this repository.

## Method and evidence levels

- **Machine-instruction verified:** imports/exports, call sites, immediate values and generic Windows DDE message codes were checked against original x86 PE bytes and, where possible, validated using `tools/verify_binary_edges.py`.
- **Cross-checked with saved `.NSK` records:** generated prefix and descriptor templates were compared with *archived* `nc_tea.nsk`, `ch_tea.nsk` and `ax_tea.nsk` files.
- **Not demonstrated:** a complete call chain from selecting a specific MD on an HMI screen to the byte-level DDE request and subsequent display, or proof that archived `.NSK` files were loaded by the runtime server.

## PE identity (historical static-analysis corpus)

Original SHA256 values are provided for provenance; the files are not distributed:

| Original PE | SHA256 |
|---|---|
| `ibdrv.exe` | `dfada5f2dd3699bac4bac25ae1cd519c7ba993ea81747b0c276dd1c2cfddbbcc` |
| `sllist.dll` | `d22612235c29eba18fcd015fe4e4edf624530c04b096f6eedaec9f9901434e9e` |
| `slacx.dll` | `8dc694b60a005fcb8bfee77f255c8ea13d088de801be2c6070c0382b245e21a8` |
| `dctl.ocx` | `8a394bbc0f5e3aff49f61a7d491dc814e71d58b51b27fed805e5399586b213b0` |

The addresses below are **original PE virtual addresses** at each file's image base, not relocatable build-independent identifiers.

## Verified static edges

| Location | Observation | What it proves |
|---|---|---|
| `ibdrv.exe:0x005F2845` | imported `sllist_CreateViewVB` call | HMI drive view calls into sllist |
| `ibdrv.exe:0x005F2884` | imported `sllist_Cmd` call | second concrete sllist dependency |
| `sllist.dll:0x1000F642` | imported `Slacx_NcMap::GetMapInfo` via thunk | mapping metadata is requested from slacx |
| `sllist.dll:0x1000FD87` | imported `Slacx_NcMap::CreateNskFile` via thunk | sllist can call `.NSK` mapping generator |
| `slacx.dll:0x1000333C` | `CreateNskFile` export | binary method responsible for writing mapping descriptions |
| `slacx.dll:0x10003517` | `GetMapInfo` export | mapping table lookup implementation |
| `slacx.dll:0x1000322F` | `ConvAcxDataTyp2Ncdde` export | internal type-conversion routine |
| `dctl.ocx:0x10009DD1` | import call `USER32!PostMessageA` | actual Windows message send |
| `dctl.ocx:0x10008349` | `UnpackDDElParam` thunk | part of incoming DDE-data handler |

Other inspected DCTL locations include `0x10009C3E` (a `SendMessageA` call in its DDE initiation path), `0x100061DD` (`WM_DDE_REQUEST = 0x03E6` code) and `0x10007777` (`WM_DDE_DATA = 0x03E5` dispatch). The isolated DCTL request/receive pathway is not proof of a specific HMI MD accessing this code.

## MD prefix map reconstructed from slacx

A 22-entry x86 mapping table was located at original VA `slacx.dll:0x10030500` with 16-byte records. Representative entries:

| View | Area | Prefix | Descriptor prefix identifier |
|---:|---:|---|---|
| 1 | 0 | `/acc/nc_tea/` | `0x1A` |
| 1 | 2 | `/acc/ch_tea/` | `0x1A` |
| 1 | 3 | `/acc/ax_tea/` | `0x1A` |
| 1 | 5 | `/acc/drv_tea/` | `0x1A` |

Inside `Slacx_NcMap::CreateNskFile`, the observed text format is:

```text
LINK(%s%s,%d,"%d 1 %ld 1 %X# /NC %ld %d 11",%d)
```

For example, an archived generated Axis MD 30110 descriptor has the form:

```text
LINK(/acc/ax_tea/$MA_CTRLOUT_MODULE_NR,200,"3 1 30110 1 1A# /NC 8 0 11",10)
```

From this example, the symbolic item name, area `3`, MD number `30110`, `1A#` mapping code and `/NC 8` type token are evident. Other numeric positions must not be assigned semantics until the actual NCDDE parser has been traced. The template is used **to write mapping records**, not to perform a value read.

An offline parser checked 1,711 historical `.NSK` `LINK` records against the recovered format: 722 General, 601 Channel and 388 Axis records; **all matched** the expected structural form. Eleven of 23 separate test selectors had exact name matches across those three saved files. These numbers describe the archived corpus, **not** the active server's confirmed accessible item count.

Drive selector families `vso_tea`, `hso_tea`, `vs_pre`, `hs_pre`, or `drv_tea` must not be conflated. The tested Drive PRE address came from the older `acc6.nsk` declarations, not from the three TEA files above.

## Why this does not prove the full HMI value chain

- `Slacx_NcMap::CreateNskFile` writes `.NSK` descriptors. It does not itself return a live NCU MD value.
- `sllist_GetVbValues` (original VA `0x10016560`) transfers values into a `SAFEARRAY` in an inspected export; its lower-level live source was not recovered.
- `ibdrv.exe` `CreateViewVB` uses initial parameters `view=0x1D, area=5`, not a verified TEA value-read request for MD 30110.
- The independent API Monitor capture showed `ibmd.exe` loading `sllist.dll`, `slacx.dll`, `AB32.DLL`, `dctl.ocx`, and `dcapi.dll`. **Module load is not a call graph.** A usable original `ibmd.exe` PE was not part of this static-analysis input set.
- DCTL implements DDE messages, but this evidence alone does not establish that the particular MD screen uses DCTL to read the item of interest.

The independent NCDDE field tests bypass this missing HMI edge entirely and establish their own limited data-read result.

## Reproduce using only privately held binaries

```bash
python3 tools/verify_binary_edges.py --bin-dir /path/to/original/pe-files
```

Place the **matching versions** of `ibdrv.exe`, `sllist.dll`, `slacx.dll`, `dctl.ocx` in that folder. A different HMI version can shift all addresses and invalidate the checker. For `.NSK` format reconstruction:

```bash
python3 tools/reproduce_map.py \
  --slacx /path/to/slacx.dll \
  --sllist /path/to/sllist.dll \
  --ibdrv /path/to/ibdrv.exe \
  --nsk-dir /path/to/saved-nsk \
  --out /tmp/840d-ncmap-check
```

Do **not** commit generated `mapped_nsk_entries.tsv` or other machine-derived catalogs into the public repository. Both tools work offline and do not load Siemens code into a process.
