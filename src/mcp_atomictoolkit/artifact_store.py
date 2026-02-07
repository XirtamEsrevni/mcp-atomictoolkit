from __future__ import annotations

import mimetypes
import os
import re
import json
from contextvars import ContextVar, Token
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
_request_base_url: ContextVar[Optional[str]] = ContextVar("artifact_request_base_url", default=None)


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
    ".html",
}

_STRUCTURE_SUFFIXES = {".xyz", ".extxyz", ".cif", ".vasp", ".poscar"}


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
    request_base = _request_base_url.get()
    if request_base:
        return request_base.rstrip("/")

    base = os.environ.get("ARTIFACT_BASE_URL") or os.environ.get("PUBLIC_BASE_URL")
    if base:
        return base.rstrip("/")
    return ""


def set_request_base_url(base_url: str) -> Token:
    """Set request-scoped base URL for artifact links in the active context."""
    return _request_base_url.set(base_url.rstrip("/"))


def reset_request_base_url(token: Token) -> None:
    """Restore previous request-scoped base URL context."""
    _request_base_url.reset(token)


def _guess_artifact_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".png", ".svg", ".eps", ".pdf"}:
        return "image"
    if suffix in {".xyz", ".extxyz", ".traj", ".cif", ".vasp", ".poscar"}:
        return "structure"
    if suffix in {".csv", ".dat"}:
        return "table"
    return "file"


def _safe_html_id(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", value)


def _write_structure_preview_html(structure_path: Path, structure_url: str) -> Optional[Path]:
    """Create an embeddable HTML preview for supported structure files.

    The preview uses 3Dmol.js loaded from CDN and is intentionally self-contained
    so clients can open the generated artifact directly in a browser.
    """
    suffix = structure_path.suffix.lower()
    if suffix not in _STRUCTURE_SUFFIXES:
        return None

    parser_hint = {
        ".xyz": "xyz",
        ".extxyz": "xyz",
        ".cif": "cif",
        ".vasp": "vasp",
        ".poscar": "vasp",
    }[suffix]
    html_path = structure_path.with_suffix(f"{suffix}.preview.html")
    container_id = _safe_html_id(f"viewer_{structure_path.stem}")
    structure_url_literal = json.dumps(structure_url)

    html = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Structure Preview - {structure_path.name}</title>
  <script src=\"https://3Dmol.org/build/3Dmol-min.js\"></script>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 1rem; }}
    .viewer {{ width: 100%; height: 78vh; border: 1px solid #ddd; border-radius: 8px; }}
    .meta {{ margin-bottom: 0.75rem; }}
  </style>
</head>
<body>
  <div class=\"meta\"><strong>{structure_path.name}</strong> (format: {suffix[1:]})</div>
  <div id=\"{container_id}\" class=\"viewer\"></div>
  <script>
    (async () => {{
      const container = document.getElementById(\"{container_id}\");
      if (!container) throw new Error(\"Viewer container not found\");

      const canvas = document.createElement(\"canvas\");
      const gl = canvas.getContext(\"webgl\") || canvas.getContext(\"experimental-webgl\");
      if (!gl) {{
        throw new Error(\"WebGL is unavailable in this environment, so the interactive viewer cannot be created.\");
      }}

      const response = await fetch({structure_url_literal});
      if (!response.ok) throw new Error(`Failed to fetch structure file: ${{response.status}}`);
      const data = await response.text();

      const viewer = $3Dmol.createViewer(container, {{
        backgroundColor: \"white\"
      }});
      if (!viewer) throw new Error(\"Failed to initialize 3Dmol viewer\");
      viewer.addModel(data, \"{parser_hint}\");
      viewer.setStyle({{}}, {{stick: {{}}, sphere: {{scale: 0.3}}}});
      viewer.zoomTo();
      viewer.render();
    }})().catch((error) => {{
      const target = document.getElementById(\"{container_id}\");
      target.innerHTML = `<pre style=\"padding:1rem;color:#b00\">${{error}}</pre>`;
    }});
  </script>
</body>
</html>
"""
    html_path.write_text(html, encoding="utf-8")
    return html_path


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

        preview_html = _write_structure_preview_html(record.filepath, rel_url)
        if preview_html and preview_html.exists():
            preview_record = artifact_store.register(preview_html)
            preview_rel_url = f"/artifacts/{preview_record.artifact_id}/{preview_record.filepath.name}"
            artifacts.append(
                {
                    "label": f"{label}_preview_html",
                    "id": preview_record.artifact_id,
                    "artifact_type": "html_preview",
                    "mimeType": "text/html",
                    "filepath": str(preview_record.filepath),
                    "download_url": f"{base_url}{preview_rel_url}" if base_url else preview_rel_url,
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
