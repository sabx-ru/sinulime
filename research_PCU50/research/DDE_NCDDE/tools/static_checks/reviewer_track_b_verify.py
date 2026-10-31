#!/usr/bin/env python3
"""Independent, read-only PE analysis. Writes only phase11 reviewer artifacts."""
from pathlib import Path
import json, struct
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
ROOT=Path('/root/PL'); OUT=ROOT/'research/phase11/FUNCTIONS'
old=ROOT/'PCU_old/H/mmc2/ncdde.exe'
pe=pefile.PE(str(old)); base=pe.OPTIONAL_HEADER.ImageBase
md=Cs(CS_ARCH_X86,CS_MODE_32)
ranges=[(0x448ac0,0x448bd0),(0x449160,0x4492d3),(0x449880,0x449a80),(0x44a440,0x44a730),(0x44a730,0x44ad50),(0x44ad50,0x44aea0),(0x466f20,0x467010)]
lines=[f'Input: {old}; ImageBase={base:#x}; Capstone x86-32; all addresses VA, RVA=VA-ImageBase.']
for lo,hi in ranges:
    off=pe.get_offset_from_rva(lo-base)
    lines.append(f'\nRANGE VA {lo:08X}..{hi:08X} RVA {lo-base:08X} file offset {off:08X}')
    for i in md.disasm(pe.get_data(lo-base,hi-lo),lo):
        lines.append(f'VA {i.address:08X} RVA {i.address-base:08X} bytes {i.bytes.hex(" "):<25} {i.mnemonic} {i.op_str}')
imports={}
for ent in pe.DIRECTORY_ENTRY_IMPORT:
    for imp in ent.imports:
        imports[imp.address]=ent.dll.decode()+ '!' +(imp.name.decode() if imp.name else '#'+str(imp.ordinal))
lines.append('\nIMPORTS relevant to handle/item comparison:')
for addr,name in imports.items():
    if 'Dde' in name: lines.append(f'{addr:08X} {name}')
for addr in [0x479c64,0x486bd0]:
    lines.append(f'DATA VA {addr:08X} RVA {addr-base:08X}: {pe.get_data(addr-base,32).hex(" ")}')
(OUT/'reviewer_track_b_raw.asm').write_text('\n'.join(lines)+'\n')
# Focused literal search only in old/new MCVar and ncdde; no vendor execution.
patterns={'u32_85000903_LE':bytes.fromhex('03 09 00 85'),'u32_85000903_BE':bytes.fromhex('85 00 09 03'),'ascii_hex':b'85000903','utf16_hex':'85000903'.encode('utf-16le')}
scan=[]
for tree in ['PCU_old','PCU_new']:
    for path in (ROOT/tree).rglob('*'):
        if path.is_file() and path.name.lower() in ['ncdde.exe','mcvar.dll']:
            b=path.read_bytes(); pp=pefile.PE(data=b); bb=pp.OPTIONAL_HEADER.ImageBase
            result={'path':str(path),'imagebase':hex(bb),'matches':{}}
            for name,pat in patterns.items():
                pos=0; hits=[]
                while True:
                    pos=b.find(pat,pos)
                    if pos<0: break
                    try: rva=pp.get_rva_from_offset(pos); va=bb+rva
                    except Exception: rva=va=None
                    hits.append({'offset':hex(pos),'rva':hex(rva) if rva is not None else None,'va':hex(va) if va is not None else None}); pos+=1
                result['matches'][name]=hits
            scan.append(result)
(OUT/'reviewer_track_b_error_literal_scan.json').write_text(json.dumps(scan,indent=2)+'\n')
print('Saved raw disassembly and focused literal scan.'); print(json.dumps(scan,indent=2))
