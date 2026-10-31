#!/usr/bin/env python3
"""Independent strict parser for captured NCDDE binary/text responses.

Observed frame fields are described, but no unproven value-type mapping is
applied. In particular (type=100, flag=6, eight bytes) is NOT automatically
classified as BCD time: strings can have the same shape.
"""
from pathlib import Path
from collections import Counter
import argparse, json, struct

MARKER = bytes.fromhex('f9f8f7f6')

def parse_frame(frame: bytes) -> dict:
    if len(frame) < 20:
        raise ValueError('frame shorter than 20-byte header')
    header, version, kind, flag, sequence, opaque32, payload_size = struct.unpack_from('<HHHBBII', frame)
    if header != 20 or version != 1:
        raise ValueError('unsupported header length/version')
    if frame[16:20] != MARKER:
        raise ValueError('incorrect frame marker')
    if payload_size != len(frame) - header:
        raise ValueError('payload size differs from actual bytes')
    return dict(header_length=header,version=version,field_04=kind,field_06=flag,
                sequence=sequence,field_08=opaque32,payload_length=payload_size,
                ambiguous_8byte_string_or_BCD=(kind==100 and flag==6 and payload_size==8))

def run(root: Path):
    root=Path(root)
    binary=sorted(root.glob('*_binary.bin'))
    texts=sorted(root.glob('*_text.bin'))
    failures=[]
    frames=[]
    for p in binary:
        try:
            frames.append(parse_frame(p.read_bytes()))
        except Exception as exc:
            failures.append({'file':p.name,'error':str(exc)})
    return {'binary_total':len(binary),'binary_valid':len(frames),
            'binary_errors':failures,'text_total':len(texts),
            'text_missing_NUL':[p.name for p in texts if not p.read_bytes().endswith(b'\0')],
            'ambiguous_8byte_count':sum(x['ambiguous_8byte_string_or_BCD'] for x in frames),
            'sequence_unique':len({x['sequence'] for x in frames}),
            'field_counts':{str(k):v for k,v in sorted(Counter((x['field_04'],x['field_06']) for x in frames).items())}}

if __name__ == '__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('directory',type=Path)
    args=ap.parse_args()
    res=run(args.directory)
    print(json.dumps(res,indent=2,ensure_ascii=False))
    raise SystemExit(bool(res['binary_errors'] or res['text_missing_NUL']))
