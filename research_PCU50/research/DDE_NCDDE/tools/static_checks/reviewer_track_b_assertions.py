#!/usr/bin/env python3
"""Byte assertions plus isolated arithmetic model; does not execute vendor code."""
import struct
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
p=pefile.PE('/root/PL/PCU_old/H/mmc2/ncdde.exe'); b=p.OPTIONAL_HEADER.ImageBase
expected={0x449272:'8b750c',0x449287:'83fe07',0x449299:'e888dc0100',0x4492bd:'e894dc0100',0x44a5aa:'66c705d06b48001400',0x44a5ba:'c705e06b4800f9f8f7f6',0x44aa8a:'a084684800',0x44aaa3:'668915d66b4800',0x44aab4:'fec0',0x44aab7:'a284684800',0x44a675:'68d06b4800',0x44a680:'e8736cfbff',0x4012f8:'e9539a0400',0x40203b:'e9f0860400',0x4021ad:'e98e820400',0x44ae23:'e82ec10100',0x466f56:'ff2538636c00',0x466f26:'ff251c636c00'}
for va,h in expected.items():
 raw=bytes.fromhex(h); assert p.get_data(va-b,len(raw))==raw, hex(va)
assert p.get_data(0x479c64-b,6)==b'Ncdde\0'
imports={i.address:i.name for ent in p.DIRECTORY_ENTRY_IMPORT for i in ent.imports}
assert imports[0x6c6338]==b'DdeCreateDataHandle'
assert imports[0x6c631c]==b'DdeCmpStringHandles'
for s in range(256):
 for t in range(256):
  raw=struct.pack('<H',(s<<8)|t)
  assert raw[0]==t and raw[1]==s
assert ((255+1)&255)==0
print(f'PASS {len(expected)} instruction-byte assertions; 2 import identities; six-byte source; exhaustive 65536-pair packing model; byte wrap model')
# Confirm correct parsing distinction for header prefix 14 00 01 00.
raw=bytes.fromhex('14000100')
assert struct.unpack('<HH',raw)==(20,1)
assert struct.unpack('<I',raw)[0]!=20
print('PASS header prefix is WORD 20 / WORD 1; DWORD == 20 predicate rejects this prefix')
