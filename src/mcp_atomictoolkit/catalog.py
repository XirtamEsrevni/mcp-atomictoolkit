"""Lightweight file-based catalog of models, datasets, and potentials."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4


def _catalog_path() -> Path:
    override = os.environ.get("ATOMIC_TOOLKIT_CATALOG")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".atomictoolkit" / "catalog.json"


def _load() -> Dict:
    path = _catalog_path()
    if not path.exists():
        return {"entries": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"entries": []}
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        return {"entries": []}
    return data


def _save(data: Dict) -> None:
    path = _catalog_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def list_catalog_entries(kind: Optional[str] = None) -> Dict:
    """List catalog entries, optionally filtered by kind."""
    data = _load()
    entries = data["entries"]
    if kind:
        kind_norm = kind.strip().lower()
        entries = [e for e in entries if str(e.get("kind", "")).lower() == kind_norm]
    return {"entries": entries, "catalog_path": str(_catalog_path())}


def register_catalog_entry(
    name: str,
    kind: str,
    uri: str,
    metadata: Optional[Dict] = None,
) -> Dict:
    """Register or update a catalog entry by name+kind."""
    if not name or not name.strip():
        raise ValueError("name is required")
    if not kind or not kind.strip():
        raise ValueError("kind is required")
    if not uri or not uri.strip():
        raise ValueError("uri is required")
    kind_norm = kind.strip().lower()
    allowed = {"model", "dataset", "potential", "calculator"}
    if kind_norm not in allowed:
        raise ValueError(f"kind must be one of {sorted(allowed)}")

    data = _load()
    entries: List[Dict] = data["entries"]
    existing = next(
        (e for e in entries if e.get("name") == name.strip() and e.get("kind") == kind_norm),
        None,
    )
    entry = {
        "id": existing["id"] if existing else uuid4().hex[:12],
        "name": name.strip(),
        "kind": kind_norm,
        "uri": uri.strip(),
        "metadata": metadata or {},
    }
    if existing:
        entries[:] = [entry if e is existing else e for e in entries]
        action = "updated"
    else:
        entries.append(entry)
        action = "created"
    data["entries"] = entries
    _save(data)
    return {"action": action, "entry": entry, "catalog_path": str(_catalog_path())}


def remove_catalog_entry(name: str, kind: str) -> Dict:
    """Remove an entry by name and kind."""
    if not name or not kind:
        raise ValueError("name and kind are required")
    data = _load()
    kind_norm = kind.strip().lower()
    before = len(data["entries"])
    data["entries"] = [
        e
        for e in data["entries"]
        if not (e.get("name") == name.strip() and e.get("kind") == kind_norm)
    ]
    removed = before - len(data["entries"])
    if removed:
        _save(data)
    return {"removed": removed, "catalog_path": str(_catalog_path())}
