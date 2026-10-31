from application.service import OfflineApplicationService
from persistence.filesystem import EventStore, EvidenceStore, SnapshotStore
from persistence.publication import Publication, PublicationCoordinator


def test_service_publish_is_coordinator_production_call_site(tmp_path):
    snapshots = SnapshotStore(tmp_path / 'snapshots.json')
    evidence = EvidenceStore(tmp_path / 'evidence.json')
    events = EventStore(tmp_path / 'events.json')
    coordinator = PublicationCoordinator(tmp_path / 'manifest.json', snapshots=snapshots, evidence=evidence, events=events)
    service = OfflineApplicationService(snapshots=snapshots, evidence=evidence, events=events, coordinator=coordinator)
    snapshot = {"schema":"sinumerik-core/read-only-topology/v1", "snapshot_id":"s1", "revision":1,
        "captured_at":"2025-01-01T00:00:00Z", "mode":"offline", "installation_id":"i", "completeness":"complete",
        "actual":{"availability":"unavailable","reason":"x"}, "target":{"availability":"unavailable","reason":"x"},
        "reconciliation":{"actual_snapshot_id":None,"target_snapshot_id":None,"status":"not_comparable","reason":"x","items":[],"extensions":{}},
        "evidence":[], "unresolved":[], "extensions":{}}
    assert service.publish(Publication(1, snapshot)).revision == 1
    assert coordinator.current.revision == 1
