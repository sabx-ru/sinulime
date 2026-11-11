# Evidence ledger and certainty boundaries

Every material conclusion should be classified by evidence type rather than by how plausible it sounds.

| ID | Claim | Evidence | Status |
|---|---|---|---|
| F01 | The provided XP test executable opened the local DDE conversation `ncdde\|machineswitch`. | Eight PCU logs show `CONNECTED=YES` and a valid reply. | **Observed on one PCU** |
| F02 | Selected General/Channel/Axis MD and Drive MD addresses returned bytes. | Eight one-request logs, seven MD addresses + baseline. | **Observed on one PCU** |
| F03 | The observed reply header has length 20, version 1, `F9F8F7F6` marker. | Eight stored raw frames, offline re-check. | **Verified for these frames** |
| F04 | General MD 10050 returned identical float64 payload via TEA and PRE. | Two frames, byte-for-byte comparison. | **Verified for this one MD** |
| F05 | A `(100,6)` payload in this case contains a 16-byte ASCII name. | `CHAN1` raw bytes and matching selector. | **Verified for this case** |
| S01 | sllist calls slacx mapping / generation exports. | Callsite, thunk/import/export cross-checks on matching original PE files. | **Static verified** |
| S02 | `slacx.dll` provides prefixes and a LINK formatter. | PE map table, format string, archived NSK structural check. | **Static + file cross-check** |
| S03 | DCTL contains real DDE request/data-message code. | PE instructions using `WM_DDE_REQUEST`, `PostMessageA`, `UnpackDDElParam`. | **Static verified** |
| S04 | 1,711 saved TEA entries match recovered format. | Offline parser on three saved historical NSK files. | **Offline corpus check** |
| H01 | The live HMI screen reads a particular MD through sllist → slacx → DCTL → NCDDE. | No end-to-end runtime call/argument trace. | **Unproved** |
| H02 | MCVar's particular `ReadVar` ultimately emits the observed NCDDE DDE transaction. | MCVar symbols and DDE components exist; no traced complete path. | **Unproved** |
| H03 | Every MD can be addressed dynamically without `LINK`. | No test. | **Unproved** |
| H04 | Second axis / selected drive indexing is reliable. | No paired known MD and HMI comparison. | **Unproved** |
| H05 | PLC bit monitoring works through this specific client. | No captured PLC request in the provided eight logs. | **Unproved** |
| H06 | A drive read is harmless, fresh and correctly scaled for live current. | No safety or freshness proof; earlier drive alarm incident. | **Unproved** |

## Acceptance criteria for future claims

A claim of *complete HMI-to-NCDDE MD value chain* requires: (1) verified original screen/process callsite; (2) exact MD name/index arguments; (3) proven transition to a transport request (or alternative verified transport); (4) verified response propagation to the HMI; and (5) one safe, authorized controlled real-world comparison.

A claim of *universal machine data access* additionally requires proven missing/unknown MD behavior, type/array decoding, legal access mapping, physical-axis selection, permissions, and error handling. The present evidence meets **neither** broad claim.

All recorded data are drawn from one installation and one historic static corpus. Compatibility with other software versions is not established.
