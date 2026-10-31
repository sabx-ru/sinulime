# Stage 1 — Architecture

**Status:** normative design contract; runtime/API implementation is out of scope for Stage 1  
**Schema:** `sinumerik-core/read-only-topology/v1`  
**Compatibility:** legacy v0.9.x exports are adapter inputs only

## 1. Boundaries and invariants

The core is installation-independent, read-only, deterministic, and usable from saved captures without a CNC. NiceGUI, databases, S7 transport, PDF/electrical drawing parsing, and ARC comparison are adapters or external analysis; none is a production-core dependency. Stage 1 does not implement an API, UI, monitor, topology correction, or CNC write operation.

The dependency direction is inward:

```text
API adapter -> application services -> state/evidence/resolver -> domain
                                      |                  |
                                persistence ports   decoder ports
                                                           |
                                                acquisition ports
```

* Acquisition returns immutable raw observations; it never creates relationships.
* Decoding produces typed values/TLV records plus exact source references and failures.
* Topology resolution applies named rules and emits `confirmed`, `reference_only`, or `unresolved`; it never guesses.
* Evidence is a first-class provenance chain, not a confidence score supplied by a caller.
* State Manager owns immutable Actual and Target snapshots, revisions, reconciliation, and event derivation.
* Persistence is behind `RawArtifactStore`, `SnapshotStore`, `EvidenceStore`, `EventStore`, and `JobStore` ports.
* Network adapters map versioned application contracts and cannot mutate domain state directly.

## 2. Distinct domain objects

`PhysicalDevice` is hardware; `LogicalObject` is a control/configuration object; `Channel` is an addressable functional path; `Port` is a physical interface; `Connection` is a relation between two endpoint identities; `Evidence` is provenance. A logical axis is never silently treated as its motor, and a port is never substituted for a channel.

The sole endpoint union is defined in `docs/schema/topology-v1.schema.json`: `physical_device`, `logical_object`, `channel`, `port`, or generic `object`. Every endpoint carries `object_id`, `kind`, and a kind-specific selector. `port_id` is not universally required. A `CU_LINK` is represented as a `representation` relation joining one physical device to its logical/CU representations; it is not a cable and must not be encoded as a physical `Connection`.

## 3. Identity

Stable IDs are UUIDv5 with the published namespace UUID, schema version, installation identity, object kind, and canonical source identity. Canonicalization is UTF-8 JSON with sorted keys, no insignificant whitespace, and exact field names; numeric source components are encoded as JSON numbers, not strings. The namespace is `uuid5(NAMESPACE_URL, "sinumerik-core")`; the full name is `v1|<installation_id>|<kind>|<canonical-source-json>`.

If the source identity is missing or ambiguous, issue a UUIDv5 provisional ID using the snapshot ID as an additional scope component, set `identity_status=provisional`, and keep the record unresolved. Promotion to stable is allowed only by an explicit migration mapping that retains both IDs and evidence; IDs are never promoted because an address happened to sort first.

## 4. Actual, Target, and reconciliation

`ActualSnapshot` and `TargetSnapshot` are separate immutable payloads and graph roots. They have separate source artifact sets, evidence, and record instances even where values match. A snapshot must contain both payloads for v1; an unavailable side is represented by `{ "availability": "unavailable", "reason": "..." }`, never by `null` and never as an empty graph.

Reconciliation is separate and reports `same`, `added`, `removed`, `changed`, `unresolved`, or `not_comparable`. It is comparable only when installation/schema identities match, both sides are available and complete, and every participating endpoint resolves to a compatible stable identity. A target-only record is `added` (or `not_comparable` if the selector cannot be compared); an actual-only record is `removed`; a selector mismatch is `not_comparable` with reason `selector_mismatch`; missing evidence is `unresolved`.

Measured examples only: `runs/cnc135` reports CU=5, axes=19/19, physical edges Actual/Target=58/58, CU_LINK=4; `runs/cnc152` reports 2, 6/6, 13/13, 1. These are not defaults or predictions.

## 5. Evidence gate and topology100 safety

A confirmed equipment relation requires **all** of: (1) endpoint identities including kind and selector, (2) successful decoding, (3) a `rule_id` and immutable `rule_version`, (4) every check named by that rule (including reciprocal and selector checks), and (5) one or more evidence records. Each evidence record requires a unique `evidence_id`, `artifact_id`, exact raw observation/artifact reference, endpoint identity, observed value or explicit absence, timestamp, and quality. Otherwise the relation is `reference_only` when a source reference exists, or `unresolved` when it does not.

The `topology100/evidence.py` sparse sensor rule is normative, but the current implementation does not yet satisfy it. This is a Stage 2 blocking implementation gap; Stage 1 must not be declared implementation-ready until the developer fix and contract test pass: a sensor list's original source index must travel unchanged into `source_ref.index` and into any parallel encoder lookup. Positional enumeration after filtering, sorting, or dropping sparse entries is forbidden. If the original index is absent, duplicated, or cannot identify one sensor unambiguously, the sensor and dependent relation are `unresolved` with `ambiguous_mapping`; they are never confirmed by list position.

The current legacy `evidence.json` shape is non-conforming to v1 until migrated: generic `evidence.source`/`parameter` fields, missing `evidence_id`, rule version, endpoint identity, and exact artifact reference cannot satisfy the gate. Documentation must not claim that file conforms.

## 6. Security and baseline audit

Stage 1 API posture is normative loopback-only. A server binds only loopback addresses by default; a non-loopback bind request is rejected before listening, returns/audits `REMOTE_BIND_REJECTED`, and cannot be enabled by an ordinary API parameter. Any future operator-controlled opt-in requires authentication, authorization, origin policy, audit logging, limits, and an explicit deployment configuration outside this contract.

Replay accepts artifact IDs by default. If local paths are supported, the server canonicalizes before authorization, rejects traversal, NULs, symlinks escaping an allowlisted root, non-regular files, oversize files, and unsupported formats; authorization is checked on the canonical path and the artifact hash is recorded. Network URLs are rejected.

The canonical baseline manifest is `docs/BASELINE_MANIFEST.sha256`; it covers documented baseline inputs, excludes volatile caches and the manifest itself, and is regenerated after document changes. A baseline hash manifest may be generated without changing captures: hash bytes only (SHA-256), include canonical relative path, size, and hash, and save it as an audit artifact. No manifest currently makes a legacy evidence file conform.

## 7. Decisions

Evidence gating and explicit endpoint unions trade payload size and unresolved results for auditability. Immutable separate Actual/Target graphs trade storage and traversal for safe drift detection. Filesystem replay first trades concurrent-query performance for deterministic migration. Transport-neutral application methods trade adapter code for replaceability. See `ADR-001-004.md`.
