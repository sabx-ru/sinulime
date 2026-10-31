import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
SCRIPT = HERE / "decode_typelib.py"


def outputs():
    env = os.environ.copy()
    env["MCVAR_OLD_TYPELIB"] = str(Path("/root/PL/research/MCVar/api/resources/old_TYPELIB_1_1033.bin"))
    env["MCVAR_NEW_TYPELIB"] = str(Path("/root/PL/research/MCVar/api/resources/new_TYPELIB_1_1033.bin"))
    proc = subprocess.run([sys.executable, str(SCRIPT)], check=True, capture_output=True, text=True, env=env)
    return json.loads(proc.stdout)


def test_hashes_and_full_resource_decode():
    d = outputs()
    assert d["old"]["size"] == d["new"]["size"] == 19732
    assert d["old"]["sha256"] == "0653a34a342fc6b80e9f675ff9754173b878a353744098e6eb0c9fa429c77bb3"
    assert d["new"]["sha256"] == "a7d9968596b9e9a17dff6fc2fcf4a2e2ddc65cedd28dba76eb77791b49dadfd1"
    assert d["old"]["typeinfo_count"] == d["new"]["typeinfo_count"] == 28


def test_async_and_cyclic_interface_signatures_cross_match():
    d = outputs()
    parsed = {}
    for side in ("old", "new"):
        infos = {t["name"]: t for t in d[side]["library"]["typeinfos"]}
        for name in ("IVar", "IVar2", "IReadVarAsyncCallback", "IReadVarAsyncCallback2",
                     "IWriteVarAsyncCallback", "IWriteVarAsyncCallback2", "IMCCommandAsyncCallback"):
            assert name in infos
        for iface in ("IVar", "IVar2"):
            methods = {f["name"]: f for f in infos[iface]["funcs"]}
            assert {"ReadVarAsync", "WriteVarAsync", "ReadVarCyclic", "RemoveCyclicVariables"} <= methods.keys()
            for name, memid, offset in (("ReadVarAsync", 3, 36), ("ReadVarCyclic", 5, 44), ("RemoveCyclicVariables", 6, 48)):
                fn = methods[name]
                assert fn["memid"] == memid
                assert fn["vtable_offset"] == offset
                assert fn["callconv"] == "CC_STDCALL"
                assert fn["ret"]["vt"] == "VT_HRESULT"
        callback = {f["name"]: f for f in infos["IReadVarAsyncCallback2"]["funcs"]}["OnDataChanged"]
        assert callback["memid"] == 1
        assert callback["vtable_offset"] == 28
        assert [p["name"] for p in callback["params"]] == ["Values", "TimeStamps", "ClientHandles", "Qualities", "ServerInfos", "Errors"]
        assert infos["IMCCommandAsyncCallback"]["funcs"]
        parsed[side] = infos
    assert parsed["old"] == parsed["new"]
