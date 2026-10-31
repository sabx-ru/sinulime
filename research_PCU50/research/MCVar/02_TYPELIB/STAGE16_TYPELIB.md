# Stage16 MSFT TypeLib decoding

## Route and evidence

Use `pycomtypelib==0.1.0`, a cross-platform Python MSFT-format decoder. Its package metadata identifies its parser as a Python port of Wine `oleaut32/typelib.c`, with a documented scope covering typeinfo, functions, parameters, references and custom data. It parses standalone embedded resources directly; no Windows COM runtime is needed. `requirements.txt` pins the decoder. The `.venv` is local to this stage.

Run from this directory after installing requirements into a venv at `.venv`:

```sh
python -m pip install -r requirements.txt
python decode_typelib.py --output ../reports/typelib_decode.json
python -m pip install pytest
python -m pytest -q
```

`decode_typelib.py` uses the package CLI JSON model and adds input size and SHA-256. The saved artifact contains all 28 types, methods, type descriptors, parameter flags, memids, vtable offsets and interface GUIDs. Tests independently assert both Stage15 hashes and compare all TypeInfo JSON old/new.

## Findings

Both inputs decode as `MCVARLib`, GUID `8f64c6e3-c2a4-11d2-bfca-00609792c500`, version 1.0, LCID 1033, with 28 TypeInfos each. Old/new TypeInfo payloads compare equal, including all decoded signatures. The only TypeLib JSON delta is custom-data value, represented in `typelib_decode.json`; the raw hashes remain the Stage15 hashes.

Async/cyclic interfaces include `IVar` (GUID `c48394e0-ec79-11d0-99a9-00a0246d1792`) and `IVar2` (`23ebede0-bd9b-11d1-bd5a-0080c7f7898a`), each with 12 methods in the same memid order: ReadVar=1, WriteVar=2, ReadVarAsync=3, WriteVarAsync=4, ReadVarCyclic=5, RemoveCyclicVariables=6, LookupVariables=7, Cancel=8, Suspend=9, Resume=10, Remove=11, CalculateRequestRates=12. Dispatch vtable offsets are 28 through 72 in 4-byte increments.

The parsed descriptors distinguish revisions: IVar takes required Names and in/out pServerHandles, while IVar2 makes Names and ServerHandles optional input VARIANTs. IVar ReadVarCyclic has `RevisedUpdateRates` output and optional pErrors, while IVar2 uses `pRevisedUpdateRates`; both mark pReqID in/out. IVar2 RemoveCyclicVariables includes optional ClientHandles and optional Names/ServerHandles; IVar only Names/ServerHandles. Callback2 adds TimeStamps, optional Qualities/ServerInfos/Errors to read OnDataChanged and uses ClientHandles plus optional Errors for write OnWriteComplete. Legacy callbacks expose (Values, Qualities, ClientHandles) and (Qualities, ClientHandles), respectively. Exact structured data is in the JSON artifact; opaque/raw parser internals are not interpreted beyond the package's decoded model.

## Boundary

This is an offline parser's semantic model, not an independent Windows `ITypeInfo`/`FUNCDESC` runtime read. Cross-library imported TypeInfos are not loaded from `stdole2.tlb`; the parser resolves known external interfaces by GUID/name where available. Thus these results establish what the preserved MSFT resource encodes, but are not runtime ABI validation. Full raw-segment confirmation and Windows COM runtime comparison are outside the available Linux environment.
