# Architecture and known boundaries

## Path A: client that has been exercised on PCU50

```text
src/ncdde_md_probe.c (XP x86)
  DdeInitializeA(APPCMD_CLIENTONLY)
  DdeConnect("ncdde", "machineswitch")
  DdeClientTransaction(XTYP_REQUEST, "ncddeBinary")
  DdeGetData
       |
       v
NCDDE server (Siemens installation)
  mapped DDE item: e.g. /acc/nc_tea/$MN_SYSCLOCK_CYCLE_TIME
       |
       ?  NCDDE internal fetch / cache / NCU transport not traced
       v
Binary frame to probe -> HEX / metadata -> TXT log
```

The client-to-server DDE interaction and recorded binary reply are proven for eight requests. The server's internal request path is **not** established by these captures.

## Path B: static HMI mapping research (separate)

```text
ibdrv.exe
   └── sllist_CreateViewVB -> sllist.dll
                                      ├── Slacx_NcMap::GetMapInfo -> slacx.dll
                                      └── Slacx_NcMap::CreateNskFile -> slacx.dll
                                                                            └── .NSK LINK(...)

DCTL.OCX  -- DDE request / data handler -- (server unspecified in isolated code path)

? Specific HMI MD -> DCTL request -> live NCDDE value -> HMI display
```

Only the identified static import/call edges, mapping table, and DCTL DDE message code were recovered. Generating a `.NSK LINK` mapping is **not** reading a parameter value. `ibdrv.exe` was observed to request a view with parameters (`view=0x1D`, `area=5`), which is not equivalent to the `view=1` TEA mapping. `ibmd.exe` was observed in an API Monitor trace to load several DLLs but its own PE was not available in the original static-analysis corpus.

## Path C: MCVar (parallel investigation)

The original MCVar binaries expose COM interfaces (e.g. `MCVar.Var2`) and contain DDE-related implementation details, including an `AS2NCDDE` conversion symbol. An earlier XP-compatible MCVar monitor successfully displayed live values. **This repository does not establish an exact call-by-call MCVar-to-DDE-to-NCDDE path**, and its proof of NCDDE MD access does not require such a path.

## Distinct engineering goals

- **NCDDE diagnostic access:** request already mapped names. Achieved for selected items.
- **Complete MD catalog:** enumerate valid names/types and indexes. Partial archived data only; not proven universal.
- **HMI end-to-end RE:** prove actual value path through processes and loaded components. Open.
- **PLC diagnostics:** verify one known PLC bit and type. Open.
- **Production data collector:** error handling, calibration, caching controls, service reliability, equipment safety. Out of scope.
