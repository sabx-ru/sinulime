# Contributing

Keep this project **evidence-driven and read-only**.

- Distinguish recorded field behavior, static binary observations, documentation-based interpretation, and untested hypotheses. Cite the exact original test/capture and version locally when possible.
- Do not submit Siemens binaries, full `.NSK` tables, decompiled code dumps, disk images, trace files containing personal/machine identifiers, credentials, license files, or proprietary HMI assets.
- Do not add automatic writes, PLC forcing, drive control, axis movement, address brute-forcing, or broad unattended polling.
- Add a controlled offline fixture and a test for every claimed protocol-decoder change.
- State when a result was obtained, and whether the source is a private capture, a particular original PE, or an experiment on a live PCU50.
- For potentially risky hardware tests, review [docs/safety.md](docs/safety.md) before proposing a procedure; public pull requests should not assume testing on production machinery.

Use the local offline tests before submitting:

```bash
python3 tools/verify_frames.py
python3 -m unittest discover -s tests -v
```
