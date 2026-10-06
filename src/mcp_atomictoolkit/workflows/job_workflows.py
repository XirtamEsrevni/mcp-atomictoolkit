"""Background atomistic jobs that survive an agent disconnect."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional
from uuid import uuid4

from mcp_atomictoolkit.jobs import STORE
from mcp_atomictoolkit.md_runner import run_md


def _render_step_cap() -> Optional[int]:
    explicit = os.environ.get("MEMORY_PROFILE", "").strip().lower()
    render = os.environ.get("RENDER", "").strip().lower() in {"1", "true", "yes", "on"}
    if explicit in {"full", "off", "disabled"}:
        return None
    if explicit in {"render", "lite", "free", "low"} or render or os.environ.get("RENDER_SERVICE_ID"):
        return 40
    return None


def steps_for_duration(duration_ps: float, timestep_fs: float) -> int:
    if duration_ps <= 0:
        raise ValueError("duration_ps must be positive")
    if timestep_fs <= 0:
        raise ValueError("timestep_fs must be positive")
    return max(1, int(round(duration_ps * 1000.0 / timestep_fs)))


def _job_outputs(job_id: str, output_trajectory_filepath: str) -> Dict[str, str]:
    root = Path(os.environ.get("JOBS_DIR", "jobs")) / job_id
    root.mkdir(parents=True, exist_ok=True)
    requested = Path(output_trajectory_filepath)
    name = requested.name if requested.name and requested.name != "md.extxyz" else "md.extxyz"
    return {
        "trajectory": str(root / name),
        "log": str(root / "md.log"),
        "summary": str(root / "md_summary.txt"),
    }


def submit_md_job(
    input_filepath: str,
    input_format: Optional[str] = None,
    output_trajectory_filepath: str = "md.extxyz",
    calculator_name: str = "auto",
    integrator: str = "nvt",
    timestep_fs: float = 1.0,
    temperature_K: float = 300.0,
    steps: Optional[int] = None,
    duration_ps: Optional[float] = None,
    trajectory_interval: int = 10,
    pressure_GPa: float = 0.0,
) -> Dict:
    """Start MD and return immediately with a job_id.

    100 ps at 1 fs is 100000 steps. Poll get_job(job_id) from any later call.
    """
    if duration_ps is not None:
        requested_steps = steps_for_duration(duration_ps, timestep_fs)
    elif steps is not None:
        requested_steps = int(steps)
    else:
        requested_steps = 100
    if requested_steps < 1:
        raise ValueError("steps must be at least 1")

    cap = _render_step_cap()
    applied_steps = requested_steps
    clamped = False
    if cap is not None and requested_steps > cap:
        applied_steps = cap
        clamped = True

    job_id = uuid4().hex[:12]
    outputs = _job_outputs(job_id, output_trajectory_filepath)
    params = {
        "input_filepath": input_filepath,
        "calculator_name": calculator_name,
        "integrator": integrator,
        "timestep_fs": timestep_fs,
        "temperature_K": temperature_K,
        "requested_steps": requested_steps,
        "steps": applied_steps,
        "duration_ps": duration_ps,
        "clamped_for_host": clamped,
        "simulated_time_ps": applied_steps * timestep_fs / 1000.0,
        "outputs": outputs,
    }

    def _runner(bound_job_id, progress, should_stop):
        paths = _job_outputs(bound_job_id, output_trajectory_filepath)
        return run_md(
            input_filepath=input_filepath,
            input_format=input_format,
            output_trajectory_filepath=paths["trajectory"],
            log_filepath=paths["log"],
            summary_filepath=paths["summary"],
            calculator_name=calculator_name,
            integrator=integrator,
            timestep_fs=timestep_fs,
            temperature_K=temperature_K,
            steps=applied_steps,
            trajectory_interval=max(1, trajectory_interval),
            pressure_GPa=pressure_GPa,
            progress_callback=lambda done, total: progress(
                {"completed": done, "total": total, "message": f"{done}/{total} steps"}
            ),
            should_stop=should_stop,
        )

    record = STORE.submit("md", _runner, params=params, job_id=job_id)
    record["next_action"] = f"Call get_job with job_id={record['job_id']} until status is completed, failed, or cancelled."
    return record


def get_job(job_id: str) -> Dict:
    try:
        return STORE.get(job_id)
    except KeyError as exc:
        raise ValueError(f"Unknown job_id {job_id}. Jobs live on this server process only.") from exc


def list_jobs(limit: int = 20) -> Dict:
    return {"jobs": STORE.list_jobs(limit=limit)}


def cancel_job(job_id: str) -> Dict:
    try:
        return STORE.request_cancel(job_id)
    except KeyError as exc:
        raise ValueError(f"Unknown job_id {job_id}") from exc
