# MCVar SDK boundary

This is a portable read-only acquisition orchestration package. It does not implement Siemens MCVar COM, provide a Windows COM wrapper, assert a vendor-supported address syntax, or access a PCU. `ReadOnlyAdapter` is the extension point for a separately validated transport. Adapter calls are serialized through one lock, batches preserve address order and duplicates, retry performs reconnect between attempts, and per-item outcomes distinguish quality from age/freshness.

## Layout

- `acquisition/mcvar_sdk.py`: typed observation/result model, adapter protocol, batch planner, retry/reconnect, single-flight reads and polling registry.
- `core/polling.py`: asyncio polling subscription primitive maintained alongside the client registry.
- `examples/mock_read.py`: DEMO ONLY; uses the in-memory mock and no vendor transport.
- `tests/`: offline stdlib unittest coverage.
- `nicegui_mock_app.py`: optional NiceGUI prototype, mock data only.

## Quick start

From this directory:

```sh
PYTHONPATH=. python3 examples/mock_read.py
PYTHONPATH=. python3 -m unittest discover -s tests -p 'test_*.py' -v
```

A Windows/vendor adapter must be implemented and validated separately. It should own its COM apartment/thread requirements, return a position-aligned sequence with one value/result per requested address (including duplicates and explicit missing-item markers), map source quality only when evidence supports it, and expose reconnect/close. The SDK never infers freshness from a successful read. Without a source timestamp, the observation's freshness is `unknown`; acquisition time and last local success time are separate and do not represent controller timestamps. On failure, a last good value may be retained only with unavailable quality and age-based stale state; without source time, freshness is unknown until the local retention age exceeds policy.

## Limits

The batch size defaults to 20 as an orchestration bound, not a confirmed vendor maximum. Reads are not atomic. The SDK does not coalesce requests or guarantee backend transaction count. The threaded registry polls (it is not a native event subscription); callbacks are best-effort and exceptions are contained. `close()` stops the adapter but does not close a shared client when a registry is closed. No write API is defined.

## NiceGUI prototype

Optional UI dependency: `nicegui` (install in a project-local virtual environment using `python3 -m pip install nicegui`). Run with `PYTHONPATH=. python3 nicegui_mock_app.py`. The UI is mock-only and does not establish vendor integration or production deployment readiness. NiceGUI was not installed or run in the current environment.
