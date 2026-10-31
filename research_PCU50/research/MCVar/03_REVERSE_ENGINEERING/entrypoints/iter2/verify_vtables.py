#!/usr/bin/env python3
import hashlib,json,struct
from pathlib import Path
import pefile
ROOT=Path('/root/PL')
T=ROOT/'stages/stage16_7/entrypoints/iter2'
B={
 'old':(ROOT/'PCU_old/H/mmc2/MCVar.dll','43a5c1991d98b6b6e155233a0114d7ff72bf4dec7edf58d0607da501e7d98712',{'IVar':0x1002c5e4,'IVar2':0x1002c630}),
 'new':(ROOT/'PCU_new/C/RECYCLER/S-1-5-21-4025392478-4199590385-3038547483-1005/Dc28/files/F/mmc2/MCVar.dll','5e7d955ebe7cfd52424b04e91471b7408f42bf6cc427e3d94c50bc7f4428c24a',{'IVar':0x1002d5f4,'IVar2':0x1002d640})}
EXPECTED={'old':{'IVar':{9:0x1000c3f6,11:0x1000faf0,12:0x10010bbb},'IVar2':{9:0x1000c28a,11:0x1000f93e,12:0x10010a94}},'new':{'IVar':{9:0x1000c508,11:0x1000fc02,12:0x10010ccd},'IVar2':{9:0x1000c39c,11:0x1000fa50,12:0x10010ba6}}}
res={'status':'PASS','checks':[]}
for ver,(p,h,tables) in B.items():
 data=p.read_bytes(); assert hashlib.sha256(data).hexdigest()==h
 pe=pefile.PE(str(p)); base=pe.OPTIONAL_HEADER.ImageBase; assert base==0x10000000
 for iface,va in tables.items():
  off=pe.get_offset_from_rva(va-base)
  for slot,want in EXPECTED[ver][iface].items():
   got=struct.unpack_from('<I',data,off+4*slot)[0]
   assert got==want,(ver,iface,slot,hex(got),hex(want))
   rva=got-base
   executable=any((s.Characteristics & 0x20000000) and s.VirtualAddress <= rva < s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData) for s in pe.sections)
   assert executable,(ver,iface,slot,hex(got),'target not in executable PE section')
   res['checks'].append({'version':ver,'interface':iface,'slot':slot,'vtable_va':hex(va),'target_va':hex(got),'status':'PASS'})
print(json.dumps(res,indent=2))
(T/'vtable_verification.json').write_text(json.dumps(res,indent=2)+'\n')
