from application.service import OfflineApplicationService
from persistence.filesystem import SnapshotStore, EvidenceStore, EventStore

def test_offline_service_end_to_end(tmp_path):
    s=SnapshotStore(tmp_path/'s.json'); s.put({'id':'a','representation':'graph','role':'actual','items':[{'id':'x'}]}); s.put({'id':'t','representation':'graph','role':'actual','items':[]})
    ev=EvidenceStore(tmp_path/'v.json'); ev.put({'id':'e','evidence_id':'e','artifact_id':'a','artifact_ref':{'path':'x'},'endpoint_identity':{'object_id':'o','kind':'axis'},'observed_at':'now','quality':'ok','rule_id':'r','rule_version':'1','observed_value':1})
    service=OfflineApplicationService(snapshots=s,evidence=ev,events=EventStore(tmp_path/'events.json'))
    for method,params in [('capabilities.get',{}),('health.get',{}),('snapshot.list',{}),('snapshot.get',{'snapshot_id':'a'}),('topology.query',{'snapshot_id':'a'}),('topology.reconcile',{'actual_snapshot_id':'a','target_snapshot_id':'t'}),('evidence.get',{'evidence_id':'e'})]:
        response=service.handle({'jsonrpc':'2.0','id':1,'method':method,'params':params}); assert 'result' in response

def test_reconcile_rejects_same_snapshot_id(tmp_path):
    s=SnapshotStore(tmp_path/'s.json'); s.put({'id':'same','items':[]})
    response=OfflineApplicationService(snapshots=s).handle({'jsonrpc':'2.0','id':1,'method':'topology.reconcile','params':{'actual_snapshot_id':'same','target_snapshot_id':'same'}})
    assert response['error']['code']=='NOT_COMPARABLE'
    assert response['error']['data'] == {'reason':'identity_mismatch','actual_snapshot_id':'same','target_snapshot_id':'same'}

def test_reconcile_rejects_different_representation_and_role(tmp_path):
    s=SnapshotStore(tmp_path/'s.json'); s.put({'id':'a','representation':'graph','role':'actual','items':[]}); s.put({'id':'t','representation':'table','role':'target','items':[]})
    response=OfflineApplicationService(snapshots=s).handle({'jsonrpc':'2.0','id':1,'method':'topology.reconcile','params':{'actual_snapshot_id':'a','target_snapshot_id':'t'}})
    assert response['error']['code']=='NOT_COMPARABLE'
    assert response['error']['data'] == {'reason':'representation_mismatch','actual_snapshot_id':'a','target_snapshot_id':'t'}

def test_reconcile_rejects_missing_representation_metadata_on_actual(tmp_path):
    s=SnapshotStore(tmp_path/'s.json'); s.put({'id':'a','role':'actual','items':[]}); s.put({'id':'t','representation':'graph','role':'actual','items':[]})
    response=OfflineApplicationService(snapshots=s).handle({'jsonrpc':'2.0','id':1,'method':'topology.reconcile','params':{'actual_snapshot_id':'a','target_snapshot_id':'t'}})
    assert response['error']['code']=='NOT_COMPARABLE'
    assert response['error']['data'] == {'reason':'representation_mismatch','actual_snapshot_id':'a','target_snapshot_id':'t'}


def test_reconcile_rejects_missing_role_metadata_on_target(tmp_path):
    s=SnapshotStore(tmp_path/'s.json'); s.put({'id':'a','representation':'graph','role':'actual','items':[]}); s.put({'id':'t','representation':'graph','items':[]})
    response=OfflineApplicationService(snapshots=s).handle({'jsonrpc':'2.0','id':1,'method':'topology.reconcile','params':{'actual_snapshot_id':'a','target_snapshot_id':'t'}})
    assert response['error']['code']=='NOT_COMPARABLE'
    assert response['error']['data'] == {'reason':'representation_mismatch','actual_snapshot_id':'a','target_snapshot_id':'t'}


def test_reconcile_allows_compatible_distinct_representations_and_preserves_ids(tmp_path):
    s=SnapshotStore(tmp_path/'s.json'); s.put({'id':'actual-1','representation':'graph','role':'actual','items':[]}); s.put({'id':'target-1','representation':'graph','role':'actual','items':[]})
    response=OfflineApplicationService(snapshots=s).handle({'jsonrpc':'2.0','id':1,'method':'topology.reconcile','params':{'actual_snapshot_id':'actual-1','target_snapshot_id':'target-1'}})
    assert response['result']['reconciliation']['status']=='not_comparable'

