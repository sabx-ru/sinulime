# Stage 0 — Baseline report

**Repository:** `/root/v0.9.4`  
**Measured at:** `2026-10-26T12:00:01-05:00` (`date -Is`)  
**Mode:** offline only; no live CNC connection

## Exact verification commands and results

### Pytest

```text
$ .venv-test/bin/python -m pytest -q
...............................................                      [100%]
47 passed, 4 subtests passed in 21.59s
```

### unittest

The generic root discovery command was also checked:

```text
$ .venv-test/bin/python -m unittest discover -q
Ran 0 tests in 0.000s
NO TESTS RAN
```

It does not discover this repository's tests from the root. The repository test directory was then run explicitly:

```text
$ .venv-test/bin/python -m unittest discover -s tests -p 'test*.py' -q
----------------------------------------------------------------------
Ran 47 tests in 21.440s

OK
```

Thus the required unittest baseline is **47 passed** when run against `tests/` explicitly.

## Captured snapshot measurements

Measured from `runs/cnc135/summary.json` and `runs/cnc152/summary.json`:

| Snapshot | CU | axes | physical edges | CU_LINK |
|---|---:|---:|---:|---:|
| `cnc135` | 5 | 19/19 | 58 actual / 58 target | 4 |
| `cnc152` | 2 | 6/6 | 13 actual / 13 target | 1 |

Both summaries report complete capture and complete actual/target TLV sets. Capture directories were not modified; each contains the expected 14 files, including ReadVar journals and SDB binaries.

## Read-only scan result

Source scan of the production acquisition paths confirms read-only intent and implementation: S7 SetupCommunication and ReadVar are present; source comments explicitly state no WriteVar, Download, NC MD writes, shell/archive creation or drive-control function. No ARC creation, motion command or PLC-write operation was introduced or exercised by Stage 0.

## Limitations

- `git` is unavailable (`git: command not found`), so no commit hash or branch claim is made.
- Live CNC was not tested and no network connection was attempted.
- The generic unittest discovery command is not a valid repository test command unless `-s tests` is supplied.
- Stage 0 creates documentation only; it does not fix production issues, move `cross_validate.py`, parse PDF/electrical/ARC sources, or alter captures/runs.
