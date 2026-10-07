"""Background nudged elastic band for a simple hop."""

from __future__ import annotations

import os

import numpy as np
from pathlib import Path
from typing import Dict, Optional
from uuid import uuid4

from ase.io import read, write
from ase.mep import NEB
from ase.optimize import FIRE

from mcp_atomictoolkit.calculators import resolve_calculator
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


def submit_neb_job(
    initial_filepath: str,
    final_filepath: str,
    n_images: int = 3,
    calculator_name: str = "emt",
    fmax: float = 0.1,
    max_steps: int = 20,
    input_format: Optional[str] = None,
) -> Dict:
    """Start an ASE NEB and return a job_id. Poll get_job from a later session."""
    if _render_blocked():
        raise ValueError(
            "NEB is disabled on the Render memory profile. It needs several images in memory."
        )
    if n_images < 1:
        raise ValueError("n_images must be at least 1")
    if n_images > 7:
        raise ValueError("n_images must be 7 or fewer")
    if max_steps < 1:
        raise ValueError("max_steps must be at least 1")

    job_id = uuid4().hex[:12]
    out_dir = Path(os.environ.get("JOBS_DIR", "jobs")) / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    params = {
        "initial_filepath": initial_filepath,
        "final_filepath": final_filepath,
        "n_images": n_images,
        "calculator_name": calculator_name,
        "fmax": fmax,
        "max_steps": max_steps,
        "outputs": {"trajectory": str(out_dir / "neb.traj")},
    }

    def _runner(bound_job_id, progress, should_stop):
        root = Path(os.environ.get("JOBS_DIR", "jobs")) / bound_job_id
        root.mkdir(parents=True, exist_ok=True)
        initial = read(initial_filepath, format=input_format)
        final = read(final_filepath, format=input_format)
        if len(initial) != len(final):
            raise ValueError("initial and final structures must have the same atom count")
        species = sorted(set(initial.get_chemical_symbols()))
        calculator, calculator_used, calculator_errors = resolve_calculator(
            calculator_name,
            species=species,
        )
        images = [initial]
        images += [initial.copy() for _ in range(n_images)]
        images.append(final)
        neb = NEB(images, method="improvedtangent", allow_shared_calculator=True)
        neb.interpolate(mic=True)
        for image in images:
            image.calc = calculator
        progress({"completed": 0, "total": max_steps, "message": "interpolated"})
        opt = FIRE(neb, logfile=str(root / "neb.log"))
        completed = 0
        while completed < max_steps:
            if should_stop():
                energies = [float(image.get_potential_energy()) for image in images]
                return {
                    "status": "cancelled",
                    "converged": False,
                    "steps": completed,
                    "energies_eV": energies,
                    "barrier_eV": max(energies) - energies[0],
                }
            opt.run(fmax=fmax, steps=1)
            completed += 1
            forces = np.asarray(neb.get_forces())
            fmax_now = float(np.sqrt((forces ** 2).sum(axis=1)).max())
            progress({"completed": completed, "total": max_steps, "message": f"{completed}/{max_steps} fmax={fmax_now:.4f}"})
            if fmax_now <= fmax:
                break
        forces = np.asarray(neb.get_forces())
        fmax_final = float(np.sqrt((forces ** 2).sum(axis=1)).max())
        converged = fmax_final <= fmax
        energies = [float(image.get_potential_energy()) for image in images]
        barrier = max(energies) - energies[0]
        traj = root / "neb.traj"
        write(traj, images)
        message = "converged" if converged else "stopped at max_steps without meeting fmax"
        progress({"completed": completed, "total": max_steps, "message": message})
        return {
            "barrier_eV": barrier,
            "energies_eV": energies,
            "n_images": n_images,
            "converged": converged,
            "steps": completed,
            "fmax": fmax,
            "fmax_final": fmax_final,
            "max_steps": max_steps,
            "trajectory_filepath": str(traj.absolute()),
            "calculator_requested": calculator_name,
            "calculator_used": calculator_used,
            "calculator_fallbacks": calculator_errors,
        }

    record = STORE.submit("neb", _runner, params=params, job_id=job_id)
    record["next_action"] = f"Call get_job with job_id={record['job_id']} until status is completed or failed."
    return record
