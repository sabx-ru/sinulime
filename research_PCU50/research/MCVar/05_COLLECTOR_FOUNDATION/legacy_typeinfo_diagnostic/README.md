# Stage15 native x86 diagnostic scaffold

This is an offline-buildable 32-bit Windows diagnostic, not a client for MCVar. It performs read-only `HKCR` registration lookups and optionally loads an embedded TypeLib with `LoadTypeLibEx(..., REGKIND_NONE)` to enumerate type and member names. It never registers a DLL, activates a COM class, invokes an Automation method, or advises a connection point.

Build on Debian with `./BUILD_DEBIAN.sh`. Output is `stage15_diag.exe` (PE32 Intel 80386). Run on a Windows x86 host with `RUN_ALL.cmd`, or pass a DLL path directly as `stage15_diag.exe C:\\path\\MCVar.dll` to inspect its typelib. Output is JSONL to stdout; the batch scripts redirect it to the respective `results*.jsonl` files. `COLLECT_RESULTS.cmd` copies those into `collected_results*.jsonl` names in this directory.

`RUN_ASYNC.cmd` and `RUN_CYCLIC.cmd` intentionally emit the same inspection and explicit capability-gap report as the all-run. They do not make `ReadVarAsync` or `ReadVarCyclic` calls. Their names are workflow labels, not evidence that the respective functionality is executable. Exact ABI, callback signatures and lifecycle requirements remain unresolved. Do not add invocations until that contract is independently established.

Registry inspection reports presence or absence of typelib 1.0 win32 registration and the known MCVar/Trace CLSID inproc keys. It uses `KEY_READ` only. TypeInfo identities are partially rendered for GUID data; the type/member names and capability status are the useful discovery output. A failed TypeLib load emits the HRESULT as a separate JSONL record.

No Windows runtime or Wine is required to build. Runtime registry/resource inspection must be run on Windows; this Linux host cannot verify COM/TypeLib runtime behavior.
