# Evidence v1 conformance

This document is normative for the evidence validator at the application boundary. The validator runs before a snapshot or event publication is committed and before an API response is emitted. It is pure and side-effect free. JSON Schema checks shape; this document checks semantic conformance and the evidence gate.

## Required evidence

Each evidence object must contain:

- `evidence_id`, unique within the installation and immutable;
- opaque `artifact_id` resolvable through `RawArtifactStore`;
- exact `artifact_ref` with source index/reference and any byte range;
- `endpoint_identity` containing `object_id`, `kind`, and kind-specific selector;
- exactly one of `observed_value` or `observed_absent`;
- `observed_at` and `quality`;
- `rule_id` and immutable `rule_version`.

The artifact reference must identify the observation precisely enough to reproduce it. Generic `source` or `parameter` fields do not conform. The resolver records artifact size, format, canonical relative path when applicable, and SHA-256; URLs and unapproved paths are not artifact inputs.

## Confirmed relation gate

A `confirmed` connection or `representation` relation requires endpoint identities with correct kind and selector, successful decoding, the named rule and immutable version, every required rule check (including reciprocal and selector checks), and at least one conforming evidence ID. Evidence IDs must resolve to evidence in the same immutable publication. Missing, malformed, ambiguous, or conflicting evidence yields `reference_only` when a source reference exists, otherwise `unresolved`; it never yields `confirmed`.

A provisional/unknown endpoint identity keeps the relation unresolved. Sparse source indices must survive filtering and parallel lookup in `artifact_ref.source_ref.index`. Missing, duplicate, or ambiguous indices yield `unresolved` with reason `ambiguous_mapping`; list position cannot substitute for the original index.

## Validator result

A violation returns `{code, json_pointer, message}` entries. Shape failures use `SCHEMA_VIOLATION`; missing artifact/evidence references use `MISSING_REFERENCE`; gate failures use `EVIDENCE_GATE_FAILED`; ambiguous source mapping uses `AMBIGUOUS_MAPPING`. The validator must reject before atomic publication and must not repair, infer, reorder, or invent evidence.

## Contract tests

Fixtures must cover valid evidence, missing IDs, generic legacy fields, missing exact refs, absent observed value, invalid endpoint selectors, missing rule checks, empty evidence IDs, stale artifact IDs, provisional identities, and sparse/duplicate/ambiguous source indices. Assert that only fully conforming relations can be `confirmed` and that the legacy `evidence.json` shape is reported non-conforming until migrated.
