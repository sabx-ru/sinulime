"""S7 read-only acquisition with append-only journal, bounded retries, resume and snapshots.

No commands for S7 Download, S7 WriteVar, NC MD writes, shell or archive creation.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import hashlib, importlib.metadata, json, os, time
from .readvar import NckClient, NckTransportError, NckProtocolError, decode


def stamp():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')


class ConnectionLost(RuntimeError):
    """Exceeded bounded transport-error budget; snapshot remains usable."""


def address(area, block, unit, param, index):
    return (area, block, unit, param, index)


class Journal:
    def __init__(self, folder):
        self.out = Path(folder)
        self.out.mkdir(parents=True, exist_ok=True)
        self.path = self.out/'reads.jsonl'
        self.good = {}
        self.terminal = set()
        self.invalid_arrays = set()
        self.count = Counter()
        self.total = 0
        self.truncated_tail = False
        if self.path.exists():
            with self.path.open('rb') as fh:
                lines = fh.readlines()
            for i, line in enumerate(lines):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    if i == len(lines)-1:
                        self.truncated_tail = True
                        break
                    raise ValueError(f'Corrupt internal journal line {i+1}; will not resume')
                self._index(event)
            if self.truncated_tail:
                # Keep corrupted bytes separately for diagnosis; next append must
                # start after a complete JSON line, never corrupt the prior one.
                previous = self.path.read_bytes()
                last_newline = previous.rfind(b'\n')
                tail = previous[last_newline+1:]
                (self.out/'truncated_last_line.bin').write_bytes(tail)
                self.path.write_bytes(previous[:last_newline+1])
        if self.path.exists() and self.path.stat().st_size and not self.path.read_bytes().endswith(b'\n'):
            with self.path.open('ab') as f:
                f.write(b'\n')
        self.fh = self.path.open('a', encoding='utf-8', buffering=1)
        self.written = 0
        self.last_flush = time.monotonic()
        self.cache_hits = 0

    def _index(self, e):
        if e.get('kind') in ('array_invalid','array_verified'):
            cu, param = e['cu'], e['param']
            if e['kind']=='array_invalid':
                self.invalid_arrays.add((cu,param))
                self.good={k:v for k,v in self.good.items() if k[:4]!=(5,128,cu,param)}
                self.terminal={k for k in self.terminal if k[:4]!=(5,128,cu,param)}
            else:self.invalid_arrays.discard((cu,param))
            return
        if e.get('kind') != 'read' and 'area' not in e:
            return
        key = address(e.get('area'), e.get('block'), e.get('unit'), e.get('param'), e.get('index'))
        status = e.get('status')
        if status == 'ok':
            self.good[key] = e
            self.terminal.discard(key)
        elif status == 'item_error' and key not in self.good:
            self.terminal.add(key)
        self.total += 1
        self.count[str(status)] += 1

    def append(self, e):
        self.fh.write(json.dumps(e, ensure_ascii=False, separators=(',', ':'))+'\n')
        self._index(e)
        self.written += 1
        if self.written % 100 == 0 or time.monotonic()-self.last_flush > 5:
            self.flush()
        if self.written % 200 == 0:
            print(f'ReadVar new={self.written:,} cached={self.cache_hits:,} '
                  f'ok={self.count.get("ok", 0):,}', flush=True)

    def flush(self):
        self.fh.flush()
        os.fsync(self.fh.fileno())
        self.last_flush = time.monotonic()

    def close(self):
        if not self.fh.closed:
            self.flush()
            self.fh.close()


class Reader:
    """Read-only NCK collector with bounded per-address retries and health checks.

    A failed *address* is not a failed *connection*. After a configurable
    number of distinct exhausted addresses, a previously confirmed stable
    value is re-read on a fresh connection. If it responds unchanged, skip
    unsupported addresses and continue. No write requests are ever used.
    """
    def __init__(self, host, folder, timeout=8, interval_ms=200, retries=2,
                 max_consecutive_errors=6, reconnect_pause=2, client_factory=None,
                 health_retries=2):
        self.host = host
        self.client = None
        self.client_factory = client_factory or NckClient
        self.timeout = timeout
        self.interval = interval_ms/1000
        self.retries = retries
        self.health_retries = health_retries
        # Counts *failed addresses*, not failed attempts or S7 item rejections.
        self.max_consecutive_errors = max_consecutive_errors
        self.reconnect_pause = reconnect_pause
        self.journal = Journal(folder)
        self.previous_call = None
        self.consecutive_errors = 0
        self.attempts = 0
        self.health_checks = 0
        self.health_recoveries = 0
        self.failed_keys = set()

    def _client(self):
        if self.client is None:
            obj = self.client_factory(self.host, timeout=self.timeout)
            try:
                obj.connect()
            except Exception:
                try: obj.close()
                except Exception: pass
                raise
            self.client = obj
        return self.client

    def _close_client(self):
        old = self.client
        self.client = None
        if old:
            try: old.close()
            except Exception: pass

    def _pace(self):
        if self.previous_call is not None:
            wait = self.previous_call+self.interval-time.monotonic()
            if wait>0: time.sleep(wait)
        self.previous_call = time.monotonic()

    def _health_reference(self):
        # Machine configuration values, not volatile drive status counters.
        for key, event in self.journal.good.items():
            if key == address(0,26,1,13120,0) and event.get('raw_hex'):
                return key,event
        for key,event in self.journal.good.items():
            if key[:4] == (0,26,1,13120) and event.get('raw_hex'):
                return key,event
        for key,event in self.journal.good.items():
            if key[0:2] == (5,128) and key[3:] == (102,0) and event.get('raw_hex'):
                return key,event
        return None,None

    def _verify_connection(self):
        """Bounded independent probe; return False only for unavailable NCU.

        A changed baseline is a hard snapshot-consistency error, never a
        successful recovery. Diagnostic events do not replace cached reads.
        """
        key, old = self._health_reference()
        if old is None:
            self.journal.append({'utc':stamp(),'kind':'health_probe',
                                 'status':'no_baseline',
                                 'error':'No previously confirmed stable MD13120 or CU p0102'})
            return False
        self.health_checks += 1
        area,block,unit,param,index = key
        for attempt in range(self.health_retries+1):
            self._close_client()
            if attempt:
                time.sleep(min(10.0,self.reconnect_pause*(2**(attempt-1))))
            try:
                self._pace()
                packet = self._client().read(area=area,block=block,unit=unit,
                                             column=param,index=index)
                if packet['status'] != 'ok':
                    raise NckProtocolError('Health probe rejected: '+str(packet.get('status')))
                # Compare raw bytes as well as data availability; a changed
                # reference means resume/merge could mix configurations.
                if packet['raw_hex'] != old['raw_hex']:
                    self.journal.append({'utc':stamp(),'kind':'health_probe',
                        'status':'changed', 'address':list(key), 'attempt':attempt+1})
                    raise RuntimeError('Stable NCU identity/configuration value changed during capture: '
                                       +str(key)+'; refusing to merge snapshots')
                self.journal.append({'utc':stamp(),'kind':'health_probe',
                    'status':'ok','address':list(key),'attempt':attempt+1})
                self.health_recoveries += 1
                self.consecutive_errors = 0
                print(f'[health] NCU responds; continue after failed addresses '
                      f'(probe {param}[{index}])',flush=True)
                return True
            except RuntimeError:
                raise
            except (OSError,TimeoutError,NckTransportError,NckProtocolError,ValueError) as ex:
                self.journal.append({'utc':stamp(),'kind':'health_probe',
                    'status':'error','address':list(key),'attempt':attempt+1,
                    'error':f'{type(ex).__name__}: {ex}',
                    'response_hex':getattr(ex,'response_hex',None),
                    'response_length':getattr(ex,'response_length',None)})
                self._close_client()
        return False

    def read(self, area, block, unit, param, index=0, dtype='u16be', refresh=False):
        key = address(area,block,unit,param,index)
        if not refresh:
            previous = self.journal.good.get(key)
            if previous and previous.get('dtype') == dtype:
                self.journal.cache_hits += 1
                self.failed_keys.discard(key)
                return previous.get('value')
            if key in self.journal.terminal:
                self.journal.cache_hits += 1
                self.failed_keys.discard(key)
                return None

        for attempt in range(self.retries+1):
            self._pace()
            start = time.monotonic()
            status = None; value = None; raw = None; error = None
            response_hex = None; response_length = None
            try:
                packet = self._client().read(area=area,unit=unit,column=param,
                                             index=index,block=block)
                status = packet['status']
                if status == 'ok':
                    raw = packet['raw_hex']
                    try: value = decode(raw,dtype)
                    except ValueError as ex:
                        status = 'unsupported'
                        error = str(ex)
                else:
                    error = packet.get('error',str(packet.get('code')))
            except (OSError,TimeoutError,NckTransportError,NckProtocolError) as ex:
                status = ('timeout' if isinstance(ex,TimeoutError) or
                          'timed out' in str(ex).lower() else 'protocol_error')
                error = f'{type(ex).__name__}: {ex}'
                response_hex = getattr(ex,'response_hex',None)
                response_length = getattr(ex,'response_length',None)
                self._close_client()
            self.attempts += 1
            event = {'utc':stamp(),'kind':'read','area':area,'block':block,
                'unit':unit,'param':param,'index':index,'dtype':dtype,
                'status':status,'value':value,'raw_hex':raw,'error':error,
                'response_hex':response_hex,'response_length':response_length,
                'duration_ms':round((time.monotonic()-start)*1000,2),
                'attempt':attempt+1}
            self.journal.append(event)
            if status in ('ok','item_error','unsupported'):
                self.consecutive_errors = 0
                self.failed_keys.discard(key)
                return value
            # Header errors and unexpected reply status are also retryable.
            self._close_client()
            if attempt < self.retries:
                time.sleep(min(10.0,self.reconnect_pause*(2**attempt)))

        # All attempts exhausted for *one* item: retain diagnostic, then
        # continue with next independent item unless controller is unhealthy.
        self.failed_keys.add(key)
        self.consecutive_errors += 1
        print(f'[read] unresolved {area}/{block}/{unit}/{param}[{index}] '
              f'after {self.retries+1} attempts; continue',flush=True)
        if self.consecutive_errors >= self.max_consecutive_errors:
            if not self._verify_connection():
                raise ConnectionLost('NCU failed '+str(self.max_consecutive_errors)
                    +' independent addresses and '+str(self.health_retries+1)
                    +' fresh-connection health probes; capture is partial')
        return None

    def md(self, param, index=0, area=0, unit=1, dtype='u32le', refresh=False):
        return self.read(area,26,unit,param,index,dtype,refresh)

    def cu(self, cu, param, index=0, dtype='u16be', refresh=False):
        return self.read(5,128,cu,param,index,dtype,refresh)

    def servo(self, unit, param, index=0, dtype='u16be'):
        return self.read(5,130,unit,param,index,dtype)

    def close(self):
        self._close_client()
        self.journal.close()


def _sdb_meta(root):
    return {p.name:hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(Path(root).glob('SDB*.full.bin'))}


def upload_sdb(host, out, rack=0, slot=2, delay_s=0.2, resume=False, client_factory=None):
    """Read SDB20..59; re-upload on resume to ensure snapshot isn't stale.

    Existing blocks must match freshly uploaded byte-for-byte or we abort.
    In case of failure to list/upload during resume, keep existing bytes but
    mark SDB validation false. Caller must not resume live ReadVar in that case.
    """
    if client_factory is None:
        if importlib.metadata.version('python-snap7') != '2.0.2':
            raise RuntimeError('python-snap7==2.0.2 required')
        import snap7
        from snap7.type import Block
        client_factory = snap7.client.Client
    else:
        from types import SimpleNamespace
        Block = SimpleNamespace(SDB='SDB')
    root=Path(out)
    root.mkdir(parents=True, exist_ok=True)
    existing = _sdb_meta(root)
    client = None
    result = {'enumerated': [], 'success': [], 'errors': [],
              'resume_validated':False, 'original_blocks':len(existing)}
    journal = (root/'sdb_reads.jsonl').open('a',encoding='utf-8',buffering=1)
    max_attempts = 3

    def disconnect():
        nonlocal client
        if client is not None:
            try:client.disconnect()
            except Exception:pass
            client = None

    def connect():
        nonlocal client
        if client is None:
            obj=client_factory()
            try:obj.connect(host,rack,slot)
            except Exception:
                try:obj.disconnect()
                except Exception:pass
                raise
            client=obj
        return client

    try:
        for attempt in range(1,max_attempts+1):
            try:
                result['enumerated']=sorted(set(int(x) for x in
                    connect().list_blocks_of_type(Block.SDB,512)))
                break
            except Exception as ex:
                journal.write(json.dumps({'ts':stamp(),'phase':'enumerate',
                    'attempt':attempt,'status':'error',
                    'error':f'{type(ex).__name__}: {ex}'},ensure_ascii=False)+'\n')
                disconnect()
                if attempt==max_attempts:
                    raise RuntimeError(f'SDB enumeration failed after {max_attempts} attempts') from ex
                time.sleep(min(10.0,delay_s*(2**(attempt-1))))
        if len(result['enumerated'])>256:
            raise RuntimeError('Unusually large SDB list; stopped')
        interesting=[n for n in result['enumerated'] if 20<=n<60]
        if resume and existing and len(interesting)!=len(existing):
            raise RuntimeError('SDB module block set changed since previous capture')
        for n in interesting:
            filename=f'SDB{n:05d}.full.bin'
            ok=False
            for attempt in range(1,max_attempts+1):
                try:
                    contents=connect().full_upload(Block.SDB,n)
                    if isinstance(contents,tuple):
                        data=bytes(contents[0])[:int(contents[1])]
                    else:data=bytes(contents)
                    if not 1<=len(data)<=8*1024*1024:
                        raise ValueError('SDB size out of bounds')
                    digest=hashlib.sha256(data).hexdigest()
                    if resume and filename in existing and digest!=existing[filename]:
                        raise RuntimeError(f'SDB content changed: {filename}; cannot combine snapshots')
                    if resume and existing and filename not in existing:
                        raise RuntimeError(f'New SDB discovered: {filename}; cannot combine snapshots')
                    (root/filename).write_bytes(data)
                    event={'ts':stamp(),'block':n,'attempt':attempt,
                           'status':'ok','size':len(data),'sha256':digest}
                    result['success'].append(n)
                    ok=True
                except RuntimeError as ex:
                    # Snapshot-consistency violations are not retried.
                    if 'cannot combine snapshots' in str(ex):
                        raise
                    event={'ts':stamp(),'block':n,'attempt':attempt,
                           'status':'error','error':f'{type(ex).__name__}: {ex}'}
                except Exception as ex:
                    event={'ts':stamp(),'block':n,'attempt':attempt,
                           'status':'error','error':f'{type(ex).__name__}: {ex}'}
                journal.write(json.dumps(event,ensure_ascii=False)+'\n')
                if ok:break
                disconnect()
                if attempt<max_attempts:
                    time.sleep(min(10.0,delay_s*(2**(attempt-1))))
                else:result['errors'].append(event)
            time.sleep(delay_s)
        if resume and existing and len(result['success'])!=len(existing):
            raise RuntimeError('Could not revalidate all saved SDB; refusing to mix snapshots')
        result['resume_validated']=(not result['errors'] and
                                   (not existing or len(result['success'])==len(existing)))
    finally:
        disconnect()
        journal.close()
        (root/'sdb_summary.json').write_text(json.dumps(result,ensure_ascii=False,
                                                       indent=2),encoding='utf-8')
    return result


def check_resume_identity(reader):
    """Verify cached stable addresses without writing to the capture journal.

    Transient transport failures are retried on fresh connections. Any
    successfully decoded *different* value is a configuration change and is
    never accepted/retried as ordinary timeout.
    """
    keys=[]
    for idx in range(16):
        keys.append((0,26,1,13120,idx,'u32le'))
    for cu in range(1,17):
        for p in (102,9900,9902):
            key=address(5,128,cu,p,0)
            if key in reader.journal.good:
                keys.append((*key,'u16be'))
    saved=reader.journal.good
    required=[(a,b,c,d,e,t,saved[address(a,b,c,d,e)]['value'])
              for a,b,c,d,e,t in keys if address(a,b,c,d,e) in saved]
    if not required:
        raise RuntimeError('Previous journal has no readable identity values')
    client=None

    def close():
        nonlocal client
        if client:
            try:client.close()
            except Exception:pass
            client=None

    try:
        for area,block,unit,param,index,dtype,expected in required:
            for attempt in range(3):
                try:
                    if client is None:
                        obj=reader.client_factory(reader.host,timeout=reader.timeout)
                        try:obj.connect()
                        except Exception:
                            try:obj.close()
                            except Exception:pass
                            raise
                        client=obj
                    packet=client.read(area=area,block=block,unit=unit,
                                       column=param,index=index)
                    if packet['status']!='ok':
                        raise NckProtocolError('Resume identity item refused: '
                                               +str(packet.get('status')))
                    actual=decode(packet['raw_hex'],dtype)
                    if actual!=expected:
                        raise RuntimeError(
                            f'Station topology changed at {area}/{unit}/{param}[{index}]: '
                            f'previous={expected}, now={actual}')
                    break
                except (OSError,TimeoutError,NckTransportError,NckProtocolError,ValueError) as ex:
                    close()
                    if attempt==2:
                        raise RuntimeError(
                            f'Cannot verify resume identity after three attempts at '
                            f'{area}/{unit}/{param}[{index}]: {ex}') from ex
                    time.sleep(min(10,reader.reconnect_pause*(2**attempt)))
            time.sleep(max(reader.interval,0.1))
    finally:
        close()
    return len(required)


def collect_servo_properties(reader, unit):
    """Bounded read-only supplementary DO fields; missing fields stay unknown."""
    reader.servo(unit,105)
    reader.servo(unit,922)
    # p9489's live representation is unverified: keep one raw probe, never
    # use it as an identity or decode a variable name from a guessed encoding.
    reader.servo(unit,9489,0,dtype='raw')
    motor=reader.servo(unit,121,0,dtype='u8')
    if isinstance(motor,int) and motor not in (0,255):
        reader.servo(unit,125,0)
    for index in range(4):
        sensor=reader.servo(unit,141,index,dtype='u8')
        if isinstance(sensor,int) and sensor not in (0,255):
            reader.servo(unit,145,index)


def configured_cu_indices(md13120):
    """Resolve CU context numbers strictly from the MD13120 address array.

    Index 0 denotes CU1, index 1 CU2, etc. Zero means unused; a missing
    middle element is ambiguous and must not silently hide an existing CU.
    Some NCK versions reject the final (16th) probe because the array has
    only 15 elements. Permit that *trailing* rejection if 0..14 are known.
    """
    if len(md13120) != 16:
        raise ValueError('Expected 16 MD13120 probes')
    missing = [i for i, value in enumerate(md13120[:15]) if value is None]
    if missing:
        raise RuntimeError('Cannot establish CU inventory: MD13120 missing at index(es) '
                           + ', '.join(map(str,missing)) + '; no speculative CU probing')
    active = []
    for index, value in enumerate(md13120):
        if value is None:
            continue  # Known final index 15 may be unsupported.
        if not isinstance(value,int) or value<0:
            raise RuntimeError(f'Invalid MD13120[{index}] value: {value!r}')
        if value != 0:
            active.append((index+1,value))
    if not active:
        raise RuntimeError('No CU configured in MD13120; refusing blind CU scan')
    return active


def collect_nck(host, out, timeout=8, interval_ms=200, target=True,
                retries=2, max_consecutive_errors=6, reconnect_pause=2,
                on_checkpoint=None, resume=False, p978_cap=128,
                client_factory=None, health_retries=2):
    reader=Reader(host,out,timeout,interval_ms,retries,max_consecutive_errors,
                  reconnect_pause,client_factory,health_retries)
    cu=[]
    reasons=[]
    try:
        if resume and reader.journal.total:
            n=check_resume_identity(reader)
            print(f'[resume] {n} machine/array identity values verified; cached OK reads '
                  f'{len(reader.journal.good)}',flush=True)
        print('[NCK] CU inventory and NCK axes',flush=True)
        md13120 = [reader.md(13120,idx) for idx in range(16)]
        try:
            cu_contexts = configured_cu_indices(md13120)
        except RuntimeError as exc:
            # Never invent values for missing MD13120 slots. Existing readable
            # CU can still be explored, but inventory completeness is unknown.
            reasons.append('CU inventory incomplete: '+str(exc))
            cu_contexts = [(idx+1,v) for idx,v in enumerate(md13120)
                           if isinstance(v,int) and v>0]
            print('[NCK] Incomplete MD13120 inventory; probing only verified CU slots',
                  flush=True)
        print('[NCK] MD13120 configured CU contexts: '
              + ', '.join(f'CU{n}(service={service})' for n,service in cu_contexts),
              flush=True)
        counts={}
        pending=[]
        for n,service in cu_contexts:
            count=reader.cu(n,102)
            if isinstance(count,int) and 1<=count<=128:
                counts[n]=count
            else:
                pending.append((n,service))
        # NCK axes are independent of CU DO count and are always collected.
        for p in (13050,13060,10393):
            for i in range(31):reader.md(p,i)
        for i in range(31):reader.md(10000,i,dtype='raw')
        for ax in range(1,32):
            for p in (30110,30130):reader.md(p,0,area=3,unit=ax,dtype='u8')
            for p in (30220,30230,30240):
                for i in (0,1):reader.md(p,i,area=3,unit=ax,dtype='u8')
        # A CU may respond again after unrelated NCK reads/reconnection.
        for n,service in pending:
            count=reader.cu(n,102,refresh=True)
            if isinstance(count,int) and 1<=count<=128:
                counts[n]=count
                reader.failed_keys.discard(address(5,128,n,102,0))
            else:
                reasons.append(f'CU{n}: configured at MD13120[{n-1}]={service}, '
                               'but p0102 could not be read after two rounds')
                print(f'[CU{n}] p0102 unresolved; skip only this CU, continue others',
                      flush=True)
        cu=[(n,counts[n]) for n,_ in cu_contexts if n in counts]
        if on_checkpoint:on_checkpoint('NCK')
        for n,count in cu:
            print(f'[CU{n}] inventory and topology',flush=True)
            for i in range(count):
                reader.cu(n,101,i)
                reader.cu(n,107,i)
            # p0978 may contain internal separators. Stop after eight
            # documented item-level refusals, not transport failures.
            errors=0
            for idx in range(p978_cap):
                key=address(5,128,n,978,idx)
                value=reader.cu(n,978,idx,dtype='u8')
                if value is None and key in reader.journal.terminal:
                    errors+=1
                else:errors=0
                if errors>=8 and idx>=max(15,count+7):break
            for length_param,data_param in ((9900,9901),)+(((9902,9903),) if target else ()):
                length=reader.cu(n,length_param,refresh=True)
                if not isinstance(length,int) or not 0<length<=65535:
                    reasons.append(f'CU{n}.{data_param}: length {length_param} unreadable')
                    continue
                for idx in range(length):reader.cu(n,data_param,idx)
                # One deferred pass for indexes still missing after retry/reconnect.
                missing=[idx for idx in range(length) if
                         address(5,128,n,data_param,idx) not in reader.journal.good]
                if missing:
                    print(f'[CU{n}] {data_param}: retry {len(missing)} missing words',flush=True)
                    for idx in missing:
                        reader.cu(n,data_param,idx,refresh=True)
                missing=[idx for idx in range(length) if
                         address(5,128,n,data_param,idx) not in reader.journal.good]
                end=reader.cu(n,length_param,refresh=True)
                if missing or end!=length:
                    reader.journal.append({'utc':stamp(),'kind':'array_invalid',
                        'cu':n,'param':data_param,'start_count':length,'end_count':end,
                        'missing_words':len(missing), 'sample_missing_indices':missing[:30]})
                    reasons.append(f'CU{n}.{data_param}: incomplete '
                                   f'({len(missing)} missing words; length {length}->{end})')
                    print(f'[CU{n}] {data_param} incomplete; continue next block/CU',flush=True)
                    continue
                reader.journal.append({'utc':stamp(),'kind':'array_verified',
                    'cu':n,'param':data_param,'word_count':length})
            if on_checkpoint:on_checkpoint(f'CU{n}')
        # Addressing remains experimental: no invented CU/DO relation.
        servo_total=sum(1 for n,count in cu for idx in range(count)
                        if reader.journal.good.get(address(5,128,n,107,idx),{}).get('value')==11)
        print(f'[SINAMICS] Exploratory SERVO read range: {servo_total}',flush=True)
        for unit in range(1,min(servo_total,31)+1):
            typ=reader.servo(unit,107)
            if typ!=11:continue
            for idx in range(25):reader.servo(unit,199,idx)
            for p in (121,131,141,142):
                for idx in range(4):reader.servo(unit,p,idx,dtype='u8')
            collect_servo_properties(reader,unit)
        if on_checkpoint:on_checkpoint('SERVO')
        unresolved=[list(k) for k in sorted(reader.failed_keys)]
        if unresolved:
            reasons.append(f'{len(unresolved)} independent addresses unresolved after retries')
        return {'status':'incomplete' if reasons else 'complete',
                'incomplete_reasons':reasons,'unresolved_addresses':unresolved,
                'cu':cu,'new_requests':reader.attempts,
                'health_checks':reader.health_checks,
                'health_recoveries':reader.health_recoveries,
                'cache_hits':reader.journal.cache_hits,
                'totals':dict(reader.journal.count)}
    finally:
        reader.close()
