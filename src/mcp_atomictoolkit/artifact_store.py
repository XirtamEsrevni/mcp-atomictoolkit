from __future__ import annotations

import mimetypes
import os
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from time import time
from typing import Any, Dict, Iterable, List, Optional, Tuple
from uuid import uuid4


@dataclass(frozen=True)
class ArtifactRecord:
    artifact_id: str
    filepath: Path
    created_at: float


class ArtifactStore:
    """In-memory index of downloadable file artifacts."""

    def __init__(self) -> None:
        self._records: Dict[str, ArtifactRecord] = {}
        self._lock = Lock()

    def register(self, filepath: str | Path) -> ArtifactRecord:
        path = Path(filepath).expanduser().resolve()
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Artifact file not found: {path}")

        record = ArtifactRecord(
            artifact_id=f"art_{uuid4().hex}",
            filepath=path,
            created_at=time(),
        )
        with self._lock:
            self._records[record.artifact_id] = record
        return record

    def get(self, artifact_id: str) -> Optional[ArtifactRecord]:
        with self._lock:
            return self._records.get(artifact_id)


artifact_store = ArtifactStore()


_ALLOWED_SUFFIXES = {
    ".xyz",
    ".extxyz",
    ".traj",
    ".cif",
    ".vasp",
    ".poscar",
    ".png",
    ".svg",
    ".eps",
    ".pdf",
    ".csv",
    ".dat",
    ".txt",
    ".json",
    ".log",
}


def _is_artifact_candidate(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    path = Path(value).expanduser()
    if not path.exists() or not path.is_file():
        return False
    return path.suffix.lower() in _ALLOWED_SUFFIXES


def _iter_candidate_paths(data: Any) -> Iterable[Tuple[str, str]]:
    if isinstance(data, dict):
        for key, value in data.items():
            if _is_artifact_candidate(value):
                yield key, value
            else:
                yield from _iter_candidate_paths(value)
    elif isinstance(data, list):
        for item in data:
            yield from _iter_candidate_paths(item)


def _artifact_base_url() -> str:
    base = os.environ.get("ARTIFACT_BASE_URL") or os.environ.get("PUBLIC_BASE_URL")
    if base:
        return base.rstrip("/")
    return ""


def _guess_artifact_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".png", ".svg", ".eps", ".pdf"}:
        return "image"
    if suffix in {".xyz", ".extxyz", ".traj", ".cif", ".vasp", ".poscar"}:
        return "structure"
    if suffix in {".csv", ".dat"}:
        return "table"
    return "file"


def with_downloadable_artifacts(result: Dict[str, Any]) -> Dict[str, Any]:
    """Augment tool output with download URLs for generated files."""
    artifacts: List[Dict[str, Any]] = []
    base_url = _artifact_base_url()

    for label, filepath in _iter_candidate_paths(result):
        try:
            record = artifact_store.register(filepath)
        except FileNotFoundError:
            continue

        mime_type, _ = mimetypes.guess_type(record.filepath.name)
        rel_url = f"/artifacts/{record.artifact_id}/{record.filepath.name}"
        artifacts.append(
            {
                "label": label,
                "id": record.artifact_id,
                "artifact_type": _guess_artifact_type(record.filepath),
                "mimeType": mime_type or "application/octet-stream",
                "filepath": str(record.filepath),
                "download_url": f"{base_url}{rel_url}" if base_url else rel_url,
            }
        )

    if not artifacts:
        return result

    enriched = dict(result)
    enriched["artifacts"] = artifacts
    enriched["artifact_notes"] = (
        "Use download_url links to retrieve generated files; binary content is not inlined."
    )
    return enriched
