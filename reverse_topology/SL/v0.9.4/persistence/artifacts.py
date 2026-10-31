from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib, os
from application.errors import InvalidSource, NotFound

@dataclass(frozen=True)
class ArtifactMetadata:
    artifact_id: str; size: int; sha256: str; relative_path: str | None; media_type: str = "application/octet-stream"

class ArtifactResolver:
    def __init__(self, root=None, *, allow_paths=False, max_bytes=10_000_000): self.root=Path(root).resolve() if root else None; self.allow_paths=allow_paths; self.max_bytes=max_bytes
    def resolve(self, artifact_id: str) -> ArtifactMetadata:
        if not self.allow_paths or self.root is None: raise NotFound("artifact is not available")
        if not isinstance(artifact_id,str) or "\x00" in artifact_id or "://" in artifact_id: raise InvalidSource("invalid artifact path")
        candidate=Path(artifact_id)
        if not candidate.is_absolute(): candidate = self.root / candidate
        if ".." in candidate.parts: raise InvalidSource("artifact path is not allowed")
        try: real=candidate.resolve(strict=True)
        except OSError as exc: raise NotFound("artifact is not found") from exc
        if not real.is_relative_to(self.root) or not real.is_file() or candidate.is_symlink(): raise InvalidSource("artifact path is not allowed")
        size=real.stat().st_size
        if size > self.max_bytes: raise InvalidSource("artifact exceeds size limit")
        digest=hashlib.sha256(real.read_bytes()).hexdigest()
        return ArtifactMetadata(artifact_id, size, digest, real.relative_to(self.root).as_posix())
