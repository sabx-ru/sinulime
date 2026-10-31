from persistence.filesystem import SnapshotStore, EvidenceStore, EventStore

def test_file_stores_restart_and_event_retention(tmp_path):
    s=SnapshotStore(tmp_path/'s.json'); s.put({'id':'a','kind':'actual'}); assert SnapshotStore(tmp_path/'s.json').get('a')['kind']=='actual'
    e=EventStore(tmp_path/'e.json'); e.append_batch([{'id':'1','event_id':'e1','offset':1},{'id':'2','event_id':'e2','offset':2}]); assert [x['offset'] for x in e.list({},None,10)['items']]==[1,2]
    e.retain_through(1); assert e.earliest_offset()==2

def test_generation_stores_use_contract_identifier_keys(tmp_path):
    snapshots = SnapshotStore(tmp_path/'s.json')
    snapshots.put({'snapshot_id':'s1','kind':'actual'})
    assert snapshots.get('s1')['kind'] == 'actual'
    evidence = EvidenceStore(tmp_path/'e.json')
    evidence.put_batch([{'evidence_id':'ev1','value':1}])
    assert evidence.get('ev1')['value'] == 1

def test_retain_through_recovers_events_and_floor_together(tmp_path, monkeypatch):
    path = tmp_path/'e.json'
    store = EventStore(path)
    store.append_batch([{'id':'1','event_id':'e1','offset':1}, {'id':'2','event_id':'e2','offset':2}])
    original = store._floor_file.publish
    def fail_once(value):
        raise OSError('injected floor failure')
    monkeypatch.setattr(store._floor_file, 'publish', fail_once)
    try:
        store.retain_through(1)
    except OSError:
        pass
    restarted = EventStore(path)
    assert [x['offset'] for x in restarted.list({}, None, 10)['items']] == [2]
    assert restarted.earliest_offset() == 2
