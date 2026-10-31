#!/usr/bin/env python3
"""Read-only byte assertions for old ncdde.exe (PE .text raw offset == RVA here)."""
from pathlib import Path
BASE = 0x400000
IMAGE = Path('/root/PL/PCU_old/H/mmc2/ncdde.exe')
data = IMAGE.read_bytes()
checks = {
    0x449175: '2d b0 20 00 00',
    0x44917a: '0f 84 e5 00 00 00',
    0x449287: '83 fe 07',
    0x44a5a1: '8b 4c 24 18',
    0x44aa8a: 'a0 84 68 48 00',
    0x44aaa3: '66 89 15 d6 6b 48 00',
    0x44aab4: 'fe c0',
    0x44aab7: 'a2 84 68 48 00',
    0x44ae23: 'e8 2e c1 01 00',
}
for va, hx in checks.items():
    expected = bytes.fromhex(hx)
    rva = va - BASE
    got = data[rva:rva + len(expected)]
    status = 'PASS' if got == expected else 'FAIL'
    print(f'{status} VA=0x{va:08X} RVA=0x{rva:08X} bytes={got.hex()}')
    if got != expected:
        raise SystemExit(1)
needle = data[0x479c64 - BASE:0x479c64 - BASE + 6]
assert needle == b'Ncdde\0', needle.hex()
print('PASS VA=0x00479C64 source=4e6364646500 (Ncdde\\0)')
print(f'PASS {len(checks)} instruction-byte assertions; PE RVA conversion BASE=0x{BASE:X}')
