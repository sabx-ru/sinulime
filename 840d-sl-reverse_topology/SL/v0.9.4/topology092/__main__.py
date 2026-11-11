"""One-IP read-only topology collector and offline model reconstruction."""
from __future__ import annotations
import argparse, json, os, traceback
from datetime import datetime, timezone
from pathlib import Path
from .model import make_model, write_results
from .collect import collect_nck, upload_sdb, stamp, ConnectionLost

VERSION = '0.9.4'


def atomic_json(path, value):
    path=Path(path)
    temporary=path.with_name(path.name+'.tmp')
    temporary.write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf-8')
    os.replace(temporary,path)


def build_partial(root, phase, verbose=True):
    """Regenerate current topology from append-only journal, including partial CU."""
    root=Path(root)
    reads=root/'readvar'/'reads.jsonl'
    if not reads.is_file():
        return None
    try:
        doc=make_model(reads,root/'sdb')
        doc['summary']['capture_phase']=phase
        doc['summary']['scan_finished']=phase=='COMPLETE'
        doc['summary']['capture_complete']=(phase=='COMPLETE' and
            doc['summary']['hwdata_available'] and doc['summary']['topology_all_tlv_complete'])
        write_results(doc,root)
        if verbose:
            print(f'[snapshot:{phase}] axes={doc["summary"]["axes_verified"]} '
                  f'physical edges={doc["summary"]["physical_actual_edges"]}',flush=True)
        return doc
    except Exception as ex:
        (root/'snapshot_error.txt').write_text(f'{type(ex).__name__}: {ex}',encoding='utf-8')
        print(f'[snapshot:{phase}] failed: {ex}',flush=True)
        return None


def main():
    p=argparse.ArgumentParser(description=f'SINUMERIK Read-Only Topology {VERSION}')
    sub=p.add_subparsers(dest='mode',required=True)
    offline=sub.add_parser('offline',help='Rebuild topology from saved SDB/ReadVar data')
    offline.add_argument('--reads',required=True)
    offline.add_argument('--sdb',required=False,help='SDB directory, if available')
    offline.add_argument('--arrays',help='Legacy v0.8.3 topology arrays')
    offline.add_argument('--out',required=True)
    live=sub.add_parser('live',help='Read NCU without write commands')
    live.add_argument('--host',required=True)
    live.add_argument('--rack',type=int,default=0)
    live.add_argument('--slot',type=int,default=2)
    live.add_argument('--timeout',type=float,default=8)
    live.add_argument('--interval-ms',type=int,default=200)
    live.add_argument('--out',help='Capture directory; on resume use original directory')
    live.add_argument('--resume',action='store_true',help='Append only, reuse verified prior reads')
    live.add_argument('--adopt-legacy',action='store_true',help='Explicitly adopt v0.9.0 capture without manifest')
    live.add_argument('--skip-target',action='store_true')
    live.add_argument('--retries',type=int,default=2)
    live.add_argument('--max-consecutive-errors',type=int,default=6,
                      help='Failed independent addresses before a health probe (not attempts)')
    live.add_argument('--health-retries',type=int,default=2,
                      help='Additional fresh-connection health checks before giving up')
    live.add_argument('--reconnect-pause',type=float,default=2)
    live.add_argument('--p978-cap',type=int,default=128)
    args=p.parse_args()
    if args.mode=='offline':
        model=make_model(args.reads,args.sdb,args.arrays)
        write_results(model,args.out)
        print(json.dumps(model['summary'],ensure_ascii=False,indent=2),flush=True)
        return 0
    if not 100<=args.interval_ms<=10000 or not .2<=args.timeout<=30:
        p.error('interval-ms 100..10000; timeout 0.2..30')
    if not 0<=args.rack<=7 or not 0<=args.slot<=31:
        p.error('invalid rack or slot')
    if not 0<=args.retries<=3 or not 2<=args.max_consecutive_errors<=50 or not 0<=args.health_retries<=5:
        p.error('retries 0..3, max-consecutive-errors 2..50, health-retries 0..5')
    if not 0<=args.reconnect_pause<=120 or not 16<=args.p978_cap<=128:
        p.error('reconnect-pause 0..120, p978-cap 16..128')
    if args.adopt_legacy and not args.resume:p.error('--adopt-legacy requires --resume')
    if args.resume and not args.out:p.error('--resume requires --out with old capture path')
    out=Path(args.out or ('runs/'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')))
    manifest_path=out/'capture.json'
    read_dir=out/'readvar';sdb_dir=out/'sdb'
    config={'host':args.host,'rack':args.rack,'slot':args.slot,
            'target':not args.skip_target,'p978_cap':args.p978_cap}
    if args.resume:
        if not out.is_dir() or not (read_dir/'reads.jsonl').is_file():
            p.error('Existing reads.jsonl not found; cannot resume')
        if manifest_path.is_file():
            old=json.loads(manifest_path.read_text(encoding='utf-8'))
            for key,val in config.items():
                if old['config'].get(key)!=val:
                    p.error(f'Resume config mismatch: {key} ({old["config"].get(key)} != {val})')
            manifest=old
        elif args.adopt_legacy:
            manifest={'schema':'read-only-capture/v0.9.2','created':stamp(),
                      'adopted_from':'v0.9.0','config':config,'sessions':[]}
            print('Adopting v0.9.0 log with mandatory SDB and identity revalidation',flush=True)
        else:p.error('Missing capture.json; use --adopt-legacy to adopt v0.9.0 runs')
    else:
        if out.exists() and any(out.iterdir()):
            p.error('Output is not empty; use --resume, never overwrite old captures')
        manifest={'schema':'read-only-capture/v0.9.2','created':stamp(),
                  'config':config,'sessions':[]}
    out.mkdir(parents=True,exist_ok=True)
    session={'started':stamp(),'state':'running','version':VERSION}
    manifest['sessions'].append(session)
    atomic_json(manifest_path,manifest)
    phase='START';error=None
    try:
        print('[SDB] Read-only upload and SHA-256 validation',flush=True)
        try:
            result=upload_sdb(args.host,sdb_dir,args.rack,args.slot,resume=args.resume)
        except Exception as exc:
            if args.resume:
                raise  # never reuse earlier data when SDB verification failed
            (out/'sdb_error.txt').write_text(f'{type(exc).__name__}: {exc}',encoding='utf-8')
            print(f'[SDB] Unavailable ({exc}); continuing with read-only NCK collection',flush=True)
            result={'success':[],'errors':[str(exc)],'resume_validated':False}
        if args.resume and not result['resume_validated']:
            raise RuntimeError('SDB validation incomplete; refusing unsafe resume')
        phase='SDB'
        build_partial(out,phase)
        print(f'[SDB] Saved {len(result["success"])} blocks; errors={len(result["errors"])}',flush=True)
        data=collect_nck(args.host,read_dir,args.timeout,args.interval_ms,
                         not args.skip_target,args.retries,args.max_consecutive_errors,
                         args.reconnect_pause,
                         on_checkpoint=lambda step:build_partial(out,step),
                         resume=args.resume,p978_cap=args.p978_cap,
                         health_retries=args.health_retries)
        if result.get('errors') or not result.get('success'):
            data['incomplete_reasons'].append(
                'SDB upload incomplete: '
                + str(len(result.get('success',[]))) + ' blocks, '
                + str(len(result.get('errors',[]))) + ' errors')
            data['status']='incomplete'
        atomic_json(out/'readvar_result.json',data)
        if data['status']=='complete':
            phase='COMPLETE'
            return_code=0
        else:
            phase='INCOMPLETE'
            error='; '.join(data.get('incomplete_reasons',[]))
            return_code=2
    except KeyboardInterrupt:
        error='Interrupted by operator; all completed reads were preserved'
        phase='INTERRUPTED'
        return_code=130
    except (ConnectionLost, RuntimeError, OSError, ValueError) as ex:
        error=f'{type(ex).__name__}: {ex}'
        phase='INCOMPLETE'
        return_code=2
    except Exception as ex:
        error=f'{type(ex).__name__}: {ex}'
        phase='ERROR'
        (out/'traceback.txt').write_text(traceback.format_exc(),encoding='utf-8')
        return_code=3
    finally:
        session.update({'finished':stamp(),'state':phase,'error':error})
        atomic_json(manifest_path,manifest)
        doc=build_partial(out,phase)
        if error:print(f'{phase}: {error}',flush=True)
        if doc:print(json.dumps(doc['summary'],ensure_ascii=False,indent=2),flush=True)
        print('Capture:',out.resolve(),flush=True)
    return return_code


if __name__=='__main__':
    raise SystemExit(main())
