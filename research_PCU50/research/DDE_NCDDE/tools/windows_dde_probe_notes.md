# PCU_READONLY_DIAGNOSTICS

Bounded native Windows DDE client for **read-only** diagnostics. It issues at most 16 `XTYP_REQUEST` calls, uses `CF_TEXT`, has a 3-second timeout per request and a 4096-byte response bound. It never sends `XTYP_POKE`, `XTYP_EXECUTE`, advises, writes, or installs hooks.

## Build on Windows

With Visual Studio Developer Command Prompt:

```bat
cl /nologo /EHsc /W4 /std:c++17 pcu_readonly_diagnostics.cpp user32.lib /Fe:pcu_readonly_diagnostics.exe
```

With MinGW-w64:

```bat
g++ -std=c++17 -Wall -Wextra -O2 pcu_readonly_diagnostics.cpp -o pcu_readonly_diagnostics.exe -luser32
```

## Build verification

A MinGW-w64 cross-compiler was available in this environment and produced a PE32 executable from this source with only the expected GCC warning about MSVC's `#pragma comment`. This verifies source/build readiness; the executable was not run because Linux cannot host Win32 DDE or a PCU endpoint.

## Run

```bat
pcu_readonly_diagnostics.exe <service> <topic> <item> [item ...]
```

The service/topic/item strings must be supplied by an authorized Windows test operator. The program does not discover or alter PCU state. A nonzero result indicates connection/read failures or a response over the bound size.

## Exact limitations

- Linux cannot compile or run this source because it requires Win32 DDE (`windows.h`, `ddeml.h`, `user32.lib`); no PCU executable was run here.
- This is a diagnostic transport smoke harness, not a PCU protocol implementation. It does not infer item schemas, parse NCDDE binary responses, validate cache semantics, or prove transaction boundaries.
- `CF_TEXT` only is intentional and does not exercise `CF_BINARY`/NCDDE captures.
- DDE server availability, service/topic names, item permissions, bitness/session isolation, and Windows security policy remain external prerequisites.
- The saved phase11 logs and corpus are the only runtime evidence used by Track C analysis.
