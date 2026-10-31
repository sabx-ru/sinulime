# Phase11 differential results (latest preserved runtime)

## Scope and source

This artifact is derived offline from the latest preserved `real_tests` evidence. It does **not** re-run blocked tooling, access a live controller, or prove transport behavior. Primary runner: `/root/PL/real_tests/logs/RUN_ALL_21704_14346.txt`. Binary event sources: `/root/PL/real_tests/bin/logs/`. Console files under `/root/PL/real_tests/logs/console_21704_14346_*.txt` are corroboration only; bin logs drive event counts. Validator and builder scripts are under `research/phase11/SCRIPTS`; copied inputs, computed JSON, and command outputs are under `research/phase11/REAL_INPUT_CORPUS`. The exact binary predicate is `len >= 20; uint16_le(0) == 20; uint16_le(2) == 1; bytes[16:20] == F9F8F7F6`.

The copied, replayable corpus is under `/root/PL/research/phase11/REAL_INPUT_CORPUS/real_tests/` and its indexes are `provenance.json`, `counter_transitions.json`, `cases.json`, and `latest_runtime_validation.json`.

## Differential findings

- **198 binary captures** satisfy the observed schema: `len >= 20`, WORD little-endian length `20` at offset 0 (`14 00`), WORD `1` at offset 2 (`01 00`), and marker `F9 F8 F7 F6` at offset 16. The common first four bytes are exactly `14 00 01 00`.
- **197 adjacent binary transitions** match the runtime model; **0 counter mismatches**. The superseded DWORD-at-offset-0-equals-20 predicate accepts **0** real captures and is retained only as a negative control.
- DDE result counts: binary `198 DATA_HANDLE / 11 FAILED`; text `69 / 7`; OEM `0 / 23`. Failed reads remain represented by exact log/line/item/round/format evidence in `latest_runtime_validation.json`.
- MCVar: **65 rounds**, **606 requested**, **604 processed**, **2 rejected shapes** (unsupported `SAFEARRAY(VARIANT)`). Slot errors: 580 zero, 23 `0x81000303`, 1 `0x85000903`, 2 `0x80070057`; 7 rounds contain partial errors while Invoke HRESULT is zero.
- Cache modes among accepted rounds: cache 0 = 4 rounds/23 elements, cache 1 = 55/558, cache 2 = 4/23. All **63 accepted cache rounds** report `pTimeStamps` as `VT_ERROR 0x80020004`; this is a missing optional output, not a source timestamp. Dynamic `SysTimeBCD`/OLE_DATE values are kept separate.

## Exact evidence pointers

- Runner: `/root/PL/real_tests/logs/RUN_ALL_21704_14346.txt`
- Runtime ledger: `/root/PL/research/phase11/REAL_INPUT_CORPUS/latest_runtime_validation.json`
- Transition ledger: `/root/PL/research/phase11/REAL_INPUT_CORPUS/counter_transitions.json`
- Provenance pairs: `/root/PL/research/phase11/REAL_INPUT_CORPUS/provenance.json`
- Example successful binary source: `/root/PL/real_tests/bin/logs/dde_series_20261031_133529_428_pid2876.log:23` with capture `dde_series_20261031_133529_428_pid2876_r01_i03_binary.bin`.
- Example R100 failure is in that same log at line 39; associated MCVar evidence is step 27 (`B13_R_INDICES_5`) in the runtime ledger.

These are observations of one preserved runtime session. They are not transport proof, deployed-binary identity proof, an instrumented API-call trace, or a universal counter law.
