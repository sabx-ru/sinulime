# Endpoint-level cross-validation report

ARC and electrical sources remain independent observations; no runtime graph edge is created.

## Machine checks

| Machine | ARC stations | Actual components/ports/edges | Target components/ports/edges | Edge comparison | CU_LINK pairs |
|---|---:|---:|---:|---|---:|
| cnc135 | True | 95/148/58 | 110/148/58 | exact | 4 |
| cnc152 | True | 23/38/13 | 27/38/13 | exact | 1 |

## Conclusions

- **confirmed** — **endpoint records and selectors**: Actual and target component, port and edge records preserve source selectors; endpoints use component number plus port ordinal, never ordinal as identity.
- **confirmed** — **CU_LINK reciprocal representations**: CU_LINK is checked independently by exact device_id and reciprocal CU representations: cnc135=4, cnc152=1.
- **confirmed** — **ARC station inventory**: ARC is limited to station/slot presence; component, device_id and port are unavailable.
- **confirmed** — **summary preservation**: Saved v0.9.4 summary fields are compared independently for each machine.
- **rule** — **runtime graph**: No ARC/electrical observation creates or changes runtime edges.

## Explicit unavailable evidence

- ARC DP does not expose decoded component numbers, device IDs, or ports.
- PDF text does not expose stable endpoint mappings.
- Mismatch and unresolved statuses are retained; only exact endpoint evidence is confirmed.
