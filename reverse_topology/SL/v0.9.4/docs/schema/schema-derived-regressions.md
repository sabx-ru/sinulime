# Schema-derived regression checks

These checks document the structural invariants of the v1 API schema without claiming executable JSON Schema validation. They use only the Python standard library to inspect the schema document; a JSON Schema implementation remains the authoritative validator at the application boundary.

## Required regression cases

- A `RESYNC_REQUIRED` error with all five required fields in `error.data` is a valid intended payload shape.
- The generic error-data branch must exclude an object containing all `resyncData` required fields, so that the `errorData.oneOf` remains exact and non-overlapping.
- `resultEnvelope` and `pageMeta` are closed declarations, and every method-specific result leaf is closed while declaring inherited properties needed by its `allOf` composition.
- The evidence `oneOf` in `topology-v1.schema.json` remains exact: either non-null `observed_value` without `observed_absent`, or `observed_absent: true` without `observed_value`.
- Stage 3 remains a design contract only. These structural checks do not implement the API, WebSocket, identity, or sparse-sensor runtime behavior.

The repository regression test `tests/test_schema_contracts.py` checks these declarations and parses both schemas with `json.load`. It deliberately does not report a JSON Schema instance-validation result.
