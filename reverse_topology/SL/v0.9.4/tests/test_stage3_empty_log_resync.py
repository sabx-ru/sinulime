from application.service import OfflineApplicationService
from persistence.filesystem import SnapshotStore, EventStore


def test_empty_event_log_requires_resync_with_authoritative_snapshots(tmp_path):
    snapshots = SnapshotStore(tmp_path / 'snapshots.json')
    snapshots.put({'id': 'authoritative-1', 'items': []})
    events = EventStore(tmp_path / 'events.json')
    events.retain_through(20)
    response = OfflineApplicationService(snapshots=snapshots, events=events).handle({
        'jsonrpc': '2.0', 'id': 1, 'method': 'event.list',
        'params': {'from_offset': 0},
    })
    assert response['error']['code'] == 'RESYNC_REQUIRED'
    assert response['error']['data']['authoritative_snapshot_ids'] == ['authoritative-1']
    assert response['error']['data']['earliest_retained_offset'] == 21
