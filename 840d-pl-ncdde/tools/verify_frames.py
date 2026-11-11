#!/usr/bin/env python3
"""Validate recorded NCDDE binary frames offline (never connects to any device).

Examples:
    python3 tools/verify_frames.py
    python3 tools/verify_frames.py --log-zip /path/to/windows.zip
"""
import argparse
import json
import math
import re
from pathlib import Path
import struct
import sys
from zipfile import ZipFile

MARKER = bytes.fromhex('f9f8f7f6')
ROOT = Path(__file__).resolve().parents[1]


def decode_frame(data: bytes):
    if len(data) < 20:
        raise ValueError(f'frame too short: {len(data)}')
    header_len, version, value_class, value_type, sequence, count, payload_len = struct.unpack_from('<HHHBBII', data)
    if header_len != 20 or version != 1:
        raise ValueError(f'unexpected header size/version: {header_len}/{version}')
    if data[16:20] != MARKER:
        raise ValueError('missing NCDDE marker')
    payload = data[20:]
    if len(payload) != payload_len:
        raise ValueError(f'payload length {len(payload)} != declared {payload_len}')
    # These interpretations are observed for specified response pairs/lengths, not global type rules.
    pair = (value_class, value_type)
    if pair in {(1, 2), (1, 3), (1, 8)} and len(payload) == 4:
        kind, value = 'int32', struct.unpack('<i', payload)[0]
    elif pair in {(2, 5), (2, 14)} and len(payload) == 8:
        kind, value = 'float64', struct.unpack('<d', payload)[0]
    elif pair == (100, 6) and len(payload) == 16:
        kind, value = 'ascii_nul', payload.split(b'\x00', 1)[0].decode('ascii')
    else:
        kind, value = 'unknown', payload.hex().upper()
    return {
        'header_len': header_len, 'version': version, 'class': value_class,
        'type': value_type, 'sequence': sequence, 'count': count,
        'payload': payload, 'kind': kind, 'value': value,
    }


def check_fixture(path):
    obj = json.loads(Path(path).read_text(encoding='utf-8'))
    results = []
    for case in obj['frames']:
        info = decode_frame(bytes.fromhex(case['frame_hex']))
        if info['kind'] != case['decode']:
            raise AssertionError(f"{case['case']}: kind {info['kind']} != {case['decode']}")
        if info['kind'] == 'float64':
            match = math.isclose(info['value'], case['expected'], abs_tol=1e-12, rel_tol=1e-12)
        else:
            match = info['value'] == case['expected']
        if not match:
            raise AssertionError(f"{case['case']}: value {info['value']} != {case['expected']}")
        results.append((case['case'], case['item'], info))
    by_case = {case: info for case, _, info in results}
    if '01_MD_GENERAL_TEA' in by_case and '04_MD_GENERAL_PRE' in by_case:
        assert by_case['01_MD_GENERAL_TEA']['payload'] == by_case['04_MD_GENERAL_PRE']['payload'], 'General MD PRE/TEA mismatch'
    return results


def check_log_zip(path):
    results = []
    with ZipFile(path) as z:
        names = [n for n in z.namelist() if '/logs/' in n and n.lower().endswith('.txt') and not n.endswith('/EMPTY.txt')]
        if not names:
            raise ValueError('no logs/*.txt found in ZIP')
        for name in sorted(names):
            lines = z.read(name).decode('ascii').splitlines()
            fields = dict(line.split('=', 1) for line in lines if '=' in line)
            required = {'HEX', 'ITEM', 'CONNECTED', 'RESULT', 'EXIT', 'SERVICE'}
            if not required.issubset(fields):
                raise ValueError(f'{name}: missing fields {sorted(required - set(fields))}')
            if fields['CONNECTED'] != 'YES' or fields['EXIT'] != '0' or not fields['RESULT'].startswith('DATA_HANDLE'):
                raise ValueError(f'{name}: failed or incomplete request')
            if not fields['SERVICE'].startswith('ncdde ') or fields.get('MODE') != 'READ_ONLY requests=1':
                raise ValueError(f'{name}: unexpected service/mode')
            if 'FORMAT=binary' not in fields['SERVICE']:
                raise ValueError(f'{name}: expected binary reply format')
            data = bytes.fromhex(fields['HEX'])
            reported = re.search(r'length=(\d+)', fields['RESULT'])
            if not reported or int(reported.group(1)) != len(data):
                raise ValueError(f'{name}: DDE result length mismatch')
            info = decode_frame(data)
            results.append((name, fields['ITEM'], info))
    return results


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fixture', type=Path, default=ROOT/'fixtures'/'observed_frames.json')
    p.add_argument('--log-zip', type=Path, help='Optional PRIVATE raw PCU log ZIP (not included in public repo)')
    args = p.parse_args()
    rows = check_log_zip(args.log_zip) if args.log_zip else check_fixture(args.fixture)
    for name, item, info in rows:
        print(f"OK {name}: item={item} type=({info['class']},{info['type']}) value={info['value']!r} seq=0x{info['sequence']:02X}")
    print(f'PASS {len(rows)} frames validated')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (AssertionError, OSError, ValueError, KeyError, struct.error, UnicodeError) as exc:
        print(f'FAIL {exc}', file=sys.stderr)
        sys.exit(1)
