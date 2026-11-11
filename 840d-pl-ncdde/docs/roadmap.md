# Roadmap (strictly evidence-based)

## R1 — decoder quality, offline first

Implement a defensive typed decoder that uses item metadata, header class/type and payload size; reject unknown combinations instead of printing generic numeric candidates as if they were final MD values. Build a larger consented offline fixture corpus, including error replies and length mismatches. No extra on-machine reads are needed for this stage.

**Acceptance:** local fixtures pass; invalid data fail closed; every decoded type has an originating tested item or authoritative matching descriptor.

## R2 — establish indexing for an axis pair

From a documented local configuration, identify two known, permitted **static** MD values with different expected HMI values. Determine index syntax offline from relevant mappings and source analysis, then conduct only a pre-approved controlled comparison. No motion required or induced.

**Acceptance:** exact selector, index, response type, HMI-screen counterpart, and physical machine axis association are all documented. One `1` value is insufficient evidence.

## R3 — PLC status item

Choose a known documented PLC status item with local operator review. Investigate the original configuration offline before a separately authorized one-request test.

**Acceptance:** one reproducible PLC bit/state is read and compared with HMI diagnostics; no write or force behavior.

## R4 — MD outside the existing mapping set

Prove whether NCDDE supports supported documented dynamic lookup/registration for a non-listed item in the installation. Do not test blindly on production hardware and do not assume an `.NSK` item exists simply because its name looks plausible.

**Acceptance:** syntax, access rights, supported data types, error handling, and connection to a real MD are evidenced.

## R5 — complete HMI runtime call chain (independent workstream)

Get the exact `ibmd.exe` from the matching original software backup. Trace from UI-selected MD to the actual read request; distinguish `.NSK` generation from data retrieval. Validate COM/DCTL/IPC transitions before claiming that one particular Siemens module is the data transport.

**Acceptance:** all five proof criteria listed in `evidence-ledger.md` are satisfied.

## Out of scope until these are complete

Unattended services, polling every drive/PLC/MD, live drive current and servo scaling, alarms through OPC AE, control or maintenance writes, and production deployments.
