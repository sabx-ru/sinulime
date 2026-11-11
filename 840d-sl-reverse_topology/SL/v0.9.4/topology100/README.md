# topology100

`topology100` normalizes the read-only `topology092` model into an evidence schema. Runtime topology is built only from NCK ReadVar and SDB observations.

## Evidence generation

```bash
.venv-test/bin/python -m topology100 \
  --reads runs/cnc135/readvar/reads.jsonl \
  --sdb runs/cnc135/sdb \
  --out runs/v1.0.0/cnc135
```

ARC files and engineering PDFs are not inputs to this command and cannot create runtime connections.

## Endpoint-level cross-validation

```bash
.venv-test/bin/python -m topology100.cross_validate \
  --root . --out runs/v1.0.0/CROSS_VALIDATION.md
```

The command writes `CROSS_VALIDATION.md` and `CROSS_VALIDATION.json`. It reads the saved `runs/<machine>/architecture.json` model plus independent ARC/PDF sources and does not modify runtime snapshots.

The report validates, separately for `actual` and `target`:

- canonical component keys: `machine + cu + component number`;
- component records and port records with original source selectors preserved;
- unique component keys, reciprocal peer references, and selector bounds;
- endpoint-level edge comparison with `exact`, `mismatch`, and `unresolved` statuses (ordinal is never identity);
- CU_LINK pairing by exact `device_id` and reciprocal representations: cnc135 has 4 pairs, cnc152 has 1;
- actual/target deltas and v0.9.4 summary preservation.

ARC DP is limited to station/slot presence. Its component, device ID, and port fields are explicitly `unavailable`. PDF text is vocabulary evidence only; stable endpoint mapping is `unavailable`. Only exact evidence is `confirmed`; no ARC/electrical observation creates a runtime edge.
