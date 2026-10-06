"""Disk-backed jobs so an agent can disconnect and poll later.

FastMCP task ids are session-scoped and need Docket/Redis. These jobs are
plain JSON files plus a background thread, so a new MCP connection can call
get_job with the same job_id while this process is alive.
"""

from __future__ import annotations

import json
import os
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

NONTERMINAL = {"queued", "running", "cancel_requested"}


def jobs_dir() -> Path:
    path = Path(os.environ.get("JOBS_DIR", "jobs"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def max_workers() -> int:
    raw = os.environ.get("JOB_MAX_WORKERS", "1")
    try:
        value = int(raw)
    except ValueError:
        value = 1
    return max(1, value)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobStore:
    def __init__(self, root: Optional[Path] = None, worker_limit: Optional[int] = None) -> None:
        self.root = root or jobs_dir()
        self.root.mkdir(parents=True, exist_ok=True)
        self.max_workers = worker_limit if worker_limit is not None else max_workers()
        self._lock = threading.Lock()
        self._cancels: Dict[str, threading.Event] = {}
        self._slots = threading.BoundedSemaphore(self.max_workers)
        self._reconcile_stale()

    def _path(self, job_id: str) -> Path:
        return self.root / f"{job_id}.json"

    def _write(self, record: Dict[str, Any]) -> None:
        path = self._path(record["job_id"])
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(record, indent=2), encoding="utf-8")
        tmp.replace(path)

    def _reconcile_stale(self) -> None:
        """A restart has no worker for records left queued or running."""
        for path in self.root.glob("*.json"):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if record.get("status") not in NONTERMINAL:
                continue
            record["status"] = "failed"
            record["error"] = {
                "type": "ProcessRestart",
                "message": (
                    "This job was queued or running when the server process stopped. "
                    "It was not resumed. Submit a new job."
                ),
            }
            record["updated_at"] = _now()
            record["progress"] = {
                **(record.get("progress") or {}),
                "message": "lost on process restart",
            }
            self._write(record)

    def get(self, job_id: str) -> Dict[str, Any]:
        path = self._path(job_id)
        if not path.exists():
            raise KeyError(job_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def list_jobs(self, limit: int = 20) -> list[Dict[str, Any]]:
        records = []
        for path in sorted(self.root.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            try:
                records.append(json.loads(path.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                continue
            if len(records) >= limit:
                break
        return records

    def request_cancel(self, job_id: str) -> Dict[str, Any]:
        record = self.get(job_id)
        event = self._cancels.get(job_id)
        if event is not None:
            event.set()
        if record["status"] in {"completed", "failed", "cancelled"}:
            return record
        record["status"] = "cancel_requested"
        record["updated_at"] = _now()
        self._write(record)
        return record

    def submit(
        self,
        kind: str,
        runner: Callable[[str, Callable[[Dict[str, Any]], None], Callable[[], bool]], Dict[str, Any]],
        *,
        params: Dict[str, Any],
        job_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self._slots.acquire(blocking=False):
            raise RuntimeError(
                f"Job capacity full ({self.max_workers} running). "
                "Poll get_job, cancel a job, or raise JOB_MAX_WORKERS."
            )
        job_id = job_id or uuid4().hex[:12]
        cancel = threading.Event()
        record = {
            "job_id": job_id,
            "kind": kind,
            "status": "queued",
            "progress": {"completed": 0, "total": params.get("steps"), "message": "queued"},
            "params": params,
            "result": None,
            "error": None,
            "created_at": _now(),
            "updated_at": _now(),
            "reconnect": {
                "tool": "get_job",
                "job_id": job_id,
                "note": "Call get_job with this job_id from any later MCP session while the server process is alive.",
            },
        }
        with self._lock:
            self._cancels[job_id] = cancel
            self._write(record)

        def _progress(update: Dict[str, Any]) -> None:
            current = self.get(job_id)
            if current["status"] not in {"cancelled", "failed"}:
                current["status"] = "running"
            current["progress"] = {**current.get("progress", {}), **update}
            current["updated_at"] = _now()
            self._write(current)

        def _should_stop() -> bool:
            return cancel.is_set()

        def _target() -> None:
            try:
                _progress({"message": "running"})
                result = runner(job_id, _progress, _should_stop)
                current = self.get(job_id)
                if cancel.is_set():
                    current["status"] = "cancelled"
                    current["result"] = result
                else:
                    current["status"] = "completed"
                    current["result"] = result
                current["updated_at"] = _now()
                self._write(current)
            except Exception as exc:
                current = self.get(job_id)
                current["status"] = "failed"
                current["error"] = {
                    "type": exc.__class__.__name__,
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                }
                current["updated_at"] = _now()
                self._write(current)
            finally:
                with self._lock:
                    self._cancels.pop(job_id, None)
                self._slots.release()

        threading.Thread(target=_target, name=f"job-{job_id}", daemon=True).start()
        return record


STORE = JobStore()
