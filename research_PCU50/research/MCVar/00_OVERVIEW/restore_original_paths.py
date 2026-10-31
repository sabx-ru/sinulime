#!/usr/bin/env python3
"""Restore selected stage files into an arbitrary destination without overwriting."""
import argparse, csv, hashlib, shutil
from pathlib import Path
BASE=Path(__file__).resolve().parents[3]
MCVAR=BASE/'research'/'MCVar'
def main():
    ap=argparse.ArgumentParser(description='Restore curated files in original stages/ hierarchy')
    ap.add_argument('--dest',type=Path,required=True,help='Destination containing new stages/ directory (not necessarily /root/PL)')
    ap.add_argument('--dry-run',action='store_true')
    args=ap.parse_args();n=0
    rows=list(csv.DictReader((MCVAR/'00_OVERVIEW'/'FILE_MAP.csv').open(encoding='utf-8',newline='')))
    for row in rows:
        origin=Path(row['origin'])
        if not origin.parts or origin.parts[0]!='stages':continue
        if origin.is_absolute() or '..' in origin.parts:raise ValueError('unsafe origin path')
        f=BASE/row['location'];to=args.dest/origin
        b=f.read_bytes();assert hashlib.sha256(b).hexdigest()==row['sha256']
        if to.exists():
            if to.is_file() and hashlib.sha256(to.read_bytes()).hexdigest()==row['sha256']:continue
            raise FileExistsError('Refusing to overwrite '+str(to))
        if not args.dry_run:
            to.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,to)
        n+=1
    print(f'{"Would restore" if args.dry_run else "Restored"}: {n} files into {args.dest}/stages (no overwrite).')
if __name__=='__main__': main()
