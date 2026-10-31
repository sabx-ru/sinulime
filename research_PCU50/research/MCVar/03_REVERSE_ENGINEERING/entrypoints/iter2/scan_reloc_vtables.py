#!/usr/bin/env python3
"""Enumerate PE32 relocation-backed .rdata pointer tables and emit raw evidence."""
import hashlib
import json
import struct
import sys
from pathlib import Path

IMAGES = {
    "old": Path("/root/PL/PCU_old/H/mmc2/MCVar.dll"),
    "new": Path("/root/PL/PCU_new/C/RECYCLER/S-1-5-21-4025392478-4199590385-3038547483-1005/Dc28/files/F/mmc2/MCVar.dll"),
}

def scan(label, path):
    import pefile
    data = path.read_bytes()
    pe = pefile.PE(data=data, fast_load=False)
    base = pe.OPTIONAL_HEADER.ImageBase
    text = next(s for s in pe.sections if s.Name.rstrip(b"\0") == b".text")
    rdata = next(s for s in pe.sections if s.Name.rstrip(b"\0") == b".rdata")
    lo, hi = base + text.VirtualAddress, base + text.VirtualAddress + text.Misc_VirtualSize
    rlo, rhi = base + rdata.VirtualAddress, base + rdata.VirtualAddress + rdata.SizeOfRawData
    relocs = set()
    for block in pe.DIRECTORY_ENTRY_BASERELOC:
        for ent in block.entries:
            if ent.type == pefile.RELOCATION_TYPE['IMAGE_REL_BASED_HIGHLOW']:
                relocs.add(base + ent.rva)
    # Scan every aligned word; relocation marks a table boundary/anchor, not
    # every member. Keep contiguous initialized code pointers, preserving bytes.
    vals = []
    for va in range((rlo + 3) & ~3, rhi - 3, 4):
        off = pe.get_offset_from_rva(va - base)
        raw = data[off:off + 4]
        value = struct.unpack('<I', raw)[0]
        if lo <= value < hi:
            vals.append({"va": f"0x{va:08x}", "target": f"0x{value:08x}",
                         "bytes": raw.hex(), "relocation_anchor": va in relocs})
    runs = []
    for item in vals:
        va = int(item['va'], 16)
        if runs and va == int(runs[-1][-1]['va'], 16) + 4:
            runs[-1].append(item)
        else:
            runs.append([item])
    runs = [r for r in runs if len(r) >= 3]
    return {"version": label, "path": str(path), "sha256": hashlib.sha256(data).hexdigest(),
            "image_base": f"0x{base:08x}", "text_va_range": [f"0x{lo:08x}", f"0x{hi:08x}"],
            "rdata_va_range": [f"0x{rlo:08x}", f"0x{rhi:08x}"],
            "relocation_count": len(relocs), "rdata_text_pointer_count": len(vals),
            "runs": runs}

out = Path(__file__).resolve().parent
for name, image in IMAGES.items():
    result = scan(name, image)
    dest = out / f"{name}_rdata_code_pointer_runs.json"
    dest.write_text(json.dumps(result, indent=2) + "\n")
    print(dest, "runs", len(result['runs']), "pointers", result['rdata_text_pointer_count'])
