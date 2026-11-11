from pathlib import Path
import pytest
from persistence.artifacts import ArtifactResolver

def test_resolver_rejects_traversal_url_and_symlink(tmp_path):
    root=tmp_path/'root'; root.mkdir(); (root/'ok').write_bytes(b'abc')
    outside=tmp_path/'outside'; outside.write_bytes(b'x'); (root/'link').symlink_to(outside)
    resolver=ArtifactResolver(root,allow_paths=True)
    assert resolver.resolve('ok').sha256
    for value in ('../outside','https://host/x','/etc/passwd'):
        with pytest.raises(Exception): resolver.resolve(value)
    with pytest.raises(Exception): resolver.resolve('link')
