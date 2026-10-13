"""Optional Dynasor dynamical structure factor analysis as a background job."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Optional
from uuid import uuid4

import numpy as np
from ase.io import read

from mcp_atomictoolkit.jobs import STORE


def _render_blocked() -> bool:
    explicit = os.environ.get("MEMORY_PROFILE", "").strip().lower()
    if explicit in {"full", "off", "disabled"}:
        return False
    if explicit in {"render", "lite", "free", "low"}:
        return True
    return os.environ.get("RENDER", "").strip().lower() in {"1", "true", "yes", "on"} or bool(
        os.environ.get("RENDER_SERVICE_ID")
    )


def submit_dynasor_job(
    input_filepath: str,
    dt_fs: float = 5.0,
    q_max: float = 20.0,
    window_size: int = 100,
    window_step: Optional[int] = None,
    max_frames: Optional[int] = None,
    input_format: Optional[str] = None,
    calculate_currents: bool = False,
) -> Dict:
    """Start a Dynasor dynamical structure factor calculation. Poll get_job.

    Requires the optional `dynasor` package. Disabled on the Render memory profile
    because trajectories and the analysis can exceed the free dyno.
    """
    if _render_blocked():
        raise ValueError(
            "Dynasor analysis is disabled on the Render memory profile. "
            "Run it locally or on a larger host."
        )
    if dt_fs <= 0:
        raise ValueError("dt_fs must be positive")
    if q_max <= 0:
        raise ValueError("q_max must be positive")
    if window_size < 2:
        raise ValueError("window_size must be at least 2")

    try:
        import dynasor  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "dynasor is not installed. Install with `pip install dynasor` "
            "or `pip install -e '.[dynasor]'`."
        ) from exc

    job_id = uuid4().hex[:12]
    out_dir = Path(os.environ.get("JOBS_DIR", "jobs")) / job_id
    out_dir.mkdir(parents=True, exist_ok=True)

    def _runner(bound_job_id, progress, should_stop):
        from dynasor import Trajectory, compute_dynamic_structure_factors
        from dynasor.qpoints import get_spherical_qpoints

        root = Path(os.environ.get("JOBS_DIR", "jobs")) / bound_job_id
        root.mkdir(parents=True, exist_ok=True)
        if should_stop():
            return {"status": "cancelled"}

        progress({"completed": 0, "total": 3, "message": "reading trajectory"})
        # Ensure an ASE-readable trajectory is available for dynasor.
        frames = read(input_filepath, format=input_format, index=":")
        if not isinstance(frames, list):
            frames = [frames]
        if len(frames) < 2:
            raise ValueError("Trajectory must contain at least 2 frames")
        if max_frames is not None and max_frames > 0:
            frames = frames[: int(max_frames)]

        # Write a temporary extxyz that dynasor can read via ASE.
        tmp_traj = root / "trajectory.extxyz"
        from ase.io import write

        write(tmp_traj, frames, format="extxyz")

        if should_stop():
            return {"status": "cancelled"}

        progress({"completed": 1, "total": 3, "message": "computing structure factors"})
        traj = Trajectory(str(tmp_traj), trajectory_format="extxyz")
        q_points = get_spherical_qpoints(traj.cell, q_max=float(q_max))
        step = int(window_step) if window_step is not None else max(1, window_size // 5)
        sample = compute_dynamic_structure_factors(
            traj,
            q_points=q_points,
            dt=float(dt_fs),
            window_size=int(window_size),
            window_step=step,
            calculate_currents=bool(calculate_currents),
        )

        if should_stop():
            return {"status": "cancelled"}

        progress({"completed": 2, "total": 3, "message": "writing outputs"})
        # Persist a compact summary. Full sample can be large; write a reduced CSV.
        omega = np.asarray(sample.omega)
        # S is typically shape (n_q, n_omega) or similar; average over q for a quick view.
        s_array = np.asarray(getattr(sample, "S", getattr(sample, "Fqt", None)))
        if s_array is None:
            raise RuntimeError("Dynasor sample did not contain expected S or Fqt array")
        # Reduce to a 1D spectrum by averaging over q (and any extra dims except omega).
        while s_array.ndim > 1:
            s_array = s_array.mean(axis=0)
        # Align lengths if needed.
        n = min(len(omega), len(s_array))
        omega = omega[:n]
        s_avg = s_array[:n]

        csv_path = root / "dynasor_s_avg.csv"
        rows = ["omega,S_avg"]
        rows.extend(f"{float(w)},{float(s)}" for w, s in zip(omega, s_avg))
        csv_path.write_text("\n".join(rows), encoding="utf-8")

        summary = {
            "n_frames": len(frames),
            "n_qpoints": int(len(q_points)),
            "n_omega": int(n),
            "dt_fs": float(dt_fs),
            "q_max": float(q_max),
            "window_size": int(window_size),
            "calculate_currents": bool(calculate_currents),
            "outputs": {"s_avg_csv": str(csv_path)},
        }
        (root / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

        progress({"completed": 3, "total": 3, "message": "finished"})
        return summary

    STORE.submit(job_id, _runner)
    return {
        "job_id": job_id,
        "status": "submitted",
        "outputs_dir": str(out_dir),
        "note": "Poll get_job. Requires dynasor. Disabled on Render.",
    }
