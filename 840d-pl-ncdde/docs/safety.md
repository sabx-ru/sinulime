# Industrial safety and test policy

The application issues only DDE `XTYP_REQUEST` operations from the client side. **Read-only is a statement about the client's requested operation, not a certification of the machine's response.** Siemens NCDDE, the HMI, drives and PLC may contain version-, configuration-, or state-dependent behavior.

## Known historical concern

An earlier, distinct DDE experimentation period on the operator's PCU50 was followed by reported X-drive alarms, including codes `1031`, `1042`, `1043` and `1046`. **No causal link was demonstrated** between a request and those alarms. The 2026-11-11 result ZIP contains a successful Drive PRE reply but no verified post-test alarm inventory. Consequently the source repository must not present drive queries as risk-free.

## Rules for any equipment test

- Obtain explicit authorization from the machine owner/responsible technician and follow the facility's safe-state/lockout procedures.
- Ensure axis movement is prohibited, no program is running and there are no unresolved alarms. Record the machine state before testing.
- Start with the single known baseline item. A failure or new alarm is an immediate stop condition.
- Do not probe unknown addresses, attempt to brute-force index ranges, force PLC signals, request broad automatic scans, enable DDE subscriptions, or operate production machinery unattended.
- Do not test drive MD just because the C code has no write calls. Treat drive and PLC requests as requiring a separate procedure and explicit approval.
- Preserve a local incident log if equipment state changes; have an authorized technician investigate independently before considering more tests.

## Client design restrictions

- One item per file; one request per invocation; no retries.
- No POKE, EXECUTE, ADVSTART, PLC forcing, NC code transfer or configuration edits.
- A default request timeout and a size-limited captured reply.
- The drive launcher asks for manual confirmation, but **this does not replace authorization or equipment controls**.

This software must never be used as a machine-safety component, interlock, motion controller, or production data source without independent safety engineering.
