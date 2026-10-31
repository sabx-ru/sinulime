# Variable Catalogue

Machine-readable source: `VARIABLE_CATALOG.json` (copied from the evidence-backed Track D catalogue). It contains 27 literal identifiers from saved configs/logs for one observed Windows XP x86 PCU session, including 23 `CONFIRMED_READABLE` and 4 `UNSUPPORTED_IN_TEST` records. Applicability is limited to that machine/session and the historical tool versions.

No numeric NC/PLC address was inferred. Domains include `Nck.Configuration`, `Nck.State`, `Bag.State`, and Channel subareas including `State`, `Spindle`, `Parameter`, `ProgramPointer`, `ProgramInfo`, `SelectedFunctions`, and `GeometricAxis`. `R[u1,n]`-like strings are preserved literally; index semantics, datatype, bounds and portability are not inferred.

Full provenance is per-signal in JSON. A failed identifier is `UNSUPPORTED_IN_TEST` only for the observed test; it is not universal proof of unsupported hardware/software.
