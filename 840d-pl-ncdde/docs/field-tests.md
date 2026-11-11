# PCU50 field evidence — 2026-11-11

## Provenance and scope

An operator compiled the independently prepared Win32 C client on Debian, copied it to a real SINUMERIK 840D Powerline PCU50 running Windows XP and supplied the collected `windows.zip` logs for offline review. No further DDE requests were issued during this documentation effort.

Private source collection: `windows.zip`, SHA256:

```text
d18f78c2f538c43ef109b7058af9494fe391e418549518ae3e986fb7714e37e1
```

The private ZIP itself is **not** distributed in this repository. A minimized, anonymous reproduction of the eight frame byte strings is in [`../fixtures/observed_frames.json`](../fixtures/observed_frames.json). Original log filenames, host details, timestamps and PIDs were intentionally omitted from the public fixture. Test chronology below records the order of execution, not precise workstation timestamps.

**Method:** parse each log, check DDE result fields (`CONNECTED=YES`, `RESULT=DATA_HANDLE`, `EXIT=0`), decode the complete `HEX`, validate version, marker and lengths, and interpret the payload only where class/type/length and selector were consistent. Independently compare item names with privately held historical `nc6.nsk`, `acc6.nsk`, `nc_tea.nsk`, `ch_tea.nsk` and `ax_tea.nsk` files. Eight out of eight captured replies passed.

## Eight recorded test results

| # | Case | NCDDE selector | `(class,type)` | Observed decoded value | Status |
|---:|---|---|---|---|---|
| 1 | `00_BASELINE` | `/Nck/Configuration/numGlobMachAxes` | `(1,2)` | `2` | valid binary reply |
| 2 | `01_MD_GENERAL_TEA` | `/acc/nc_tea/$MN_SYSCLOCK_CYCLE_TIME` | `(2,5)` | `0.004` | valid binary reply |
| 3 | `02_MD_CHANNEL_TEA` | `/acc/ch_tea/$MC_CHAN_NAME` | `(100,6)` | `CHAN1` | valid binary reply |
| 4 | `03_MD_AXIS_TEA` | `/acc/ax_tea/$MA_CTRLOUT_MODULE_NR` | `(1,8)` | `1` | valid binary reply |
| 5 | `08_MD_DRIVE_PRE` | `/acc/vs_pre/$MD_MOTOR_NOMINAL_CURRENT` | `(2,14)` | `17.600000381469727` | valid reply; drive safety unknown |
| 6 | `04_MD_GENERAL_PRE` | `/acc/nc_pre/$MN_SYSCLOCK_CYCLE_TIME` | `(2,5)` | `0.004` | valid binary reply |
| 7 | `05_MD_CHANNEL_PRE` | `/acc/ch_pre/$MC_RESET_MODE_MASK` | `(1,3)` | `0` | valid binary reply |
| 8 | `06_MD_AXIS_PRE` | `/acc/ax_pre/$MA_AX_MOTION_DIR` | `(1,3)` | `1` | valid binary reply |

The sequence-like header byte increases `A1`, `A2`, `A3`, `A4`, `A5`, `A6`, `A7`, `A8` in this order. All eight frames use a 20-byte header, version 1 and marker `F9F8F7F6`. No captured payload was truncated; 0 failed DDE transfers are visible in these logs.

**Specific checks:**

- General TEA and PRE produce byte-identical payloads: `FCA9F1D24D62703F` (float64 `0.004`). Their full frames differ in the recorded sequence-like byte.
- Channel name payload is an ASCII/NUL-padded 16-byte field containing `CHAN1`, rather than a floating-point value even though the basic client also prints a `CANDIDATE_DOUBLE` line.
- Axis data value `1` does **not** establish whether the item is physically axis X or Y.
- Drive MD 1103 is a **nominal rating**; the record is not evidence of dynamic motor current, instantaneous load or validated scale.

## Hypotheses tested

| Hypothesis | Assessment | Basis |
|---|---|---|
| An independent 32-bit XP client can request NCDDE data | **Confirmed for these requests** | Eight successful captures |
| These particular TEA/PRE item names are readable on the tested installation | **Confirmed** | Reply per selector |
| `.NSK`-style symbolic MD addresses are operational | **Confirmed for named items** | Live replies + matching archived declarations |
| `nc_pre` and `nc_tea` return the same General MD 10050 value | **Confirmed for one MD** | Same payload bytes |
| All MD numbers are available by name | **Unproved** | No arbitrary-MD test |
| Every TEA/PRE alias has identical type and value | **Unproved / counterexample risk** | Different archived tokens for a Channel MD |
| A specific X/Y axis/drive can be chosen reliably | **Unproved** | No validated index mapping |
| PLC bit reading through this client works | **Unproved** | No PLC result in this ZIP |
| The reading always comes freshly from the NCU | **Unproved** | Cache/transport not traced |
| Drive requests are harmless | **Unproved** | Earlier incident, no post-test alarm status here |

## Source cross-checks

The offline verification originally matched all eight item names against an operator-held Siemens `.NSK` corpus. The public fixture validation can independently check the exact reply bytes and decodings but **cannot reproduce the `.NSK` cross-check without those separately sourced files**.

Run the publicly reproducible subset:

```bash
python3 tools/verify_frames.py
```

If the user has the private ZIP:

```bash
python3 tools/verify_frames.py --log-zip /path/to/windows.zip
```

This second command independently checks response framing and DDE status fields in the captured logs; it does **not** verify correctness against a Siemens `.NSK` catalog or actual hardware state.

## Safety note for the drive sample

A drive request was performed during the observed session. Earlier experiments (prior to this session) were followed by reported X-drive alarms, without an established causal mechanism. The supplied eight logs do not include a verified before/after alarm-state record. For this reason, a successful drive response is **not** a recommendation to repeat drive experiments.
