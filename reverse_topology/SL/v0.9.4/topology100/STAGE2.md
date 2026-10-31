# Stage 2 additive contracts

The Stage 2 slice adds Python-only domain/evidence contracts without changing
legacy `evidence.json` or `summary.json` outputs. `write_evidence` additionally
writes `evidence.v1.json` for replay consumers.

- `contracts.py`: immutable observation, artifact, endpoint, evidence, and envelope values; confirmed relations require stable endpoints, rules, checks, and resolvable evidence.
- `identity.py`: canonical JSON and deterministic UUIDv5 identities; missing source identity is explicitly provisional.
- `reconcile.py`: pure bidirectional Actual/Target comparison and explicit unavailable/not-comparable results.
- `adapter_legacy.py`: projects captured legacy evidence into the envelope; it never mutates source captures.

No live CNC, write operation, API, database, UI, ARC, or PDF behavior is included.
