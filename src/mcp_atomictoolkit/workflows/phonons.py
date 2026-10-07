"""Finite-displacement phonon DOS as a background job."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional, Sequence
from uuid import uuid4

import numpy as np
from ase.io import read
from ase.phonons import Phonons

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


def submit_phonon_job(
    input_filepath: str,
    calculator_name: str = "emt",
    supercell: Optional[Sequence[int]] = None,
    delta: float = 0.01,
    kpts: Optional[Sequence[int]] = None,
    npts: int = 50,
    input_format: Optional[str] = None,
) -> Dict:
    """Start a finite-displacement phonon DOS. Poll get_job. Disabled on Render."""
    if _render_blocked():
        raise ValueError("Phonon DOS is disabled on the Render memory profile.")
    supercell = [int(v) for v in (supercell or [1, 1, 1])]
    kpts = [int(v) for v in (kpts or [2, 2, 2])]
    if any(v < 1 for v in supercell) or any(v < 1 for v in kpts):
        raise ValueError("supercell and kpts values must be at least 1")
    if int(np.prod(supercell)) > 4:
        raise ValueError("supercell product must be 4 or fewer for this first phonon job")

    job_id = uuid4().hex[:12]
    out_dir = Path(os.environ.get("JOBS_DIR", "jobs")) / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    params = {
        "input_filepath": input_filepath,
        "calculator_name": calculator_name,
        "supercell": supercell,
        "kpts": kpts,
        "npts": npts,
        "outputs": {"dos": str(out_dir / "phonon_dos.csv")},
    }

    def _runner(bound_job_id, progress, should_stop):
        root = Path(os.environ.get("JOBS_DIR", "jobs")) / bound_job_id
        root.mkdir(parents=True, exist_ok=True)
        if should_stop():
            return {"status": "cancelled"}
        atoms = read(input_filepath, format=input_format)
        species = sorted(set(atoms.get_chemical_symbols()))
        calculator, calculator_used, calculator_errors = resolve_calculator(
            calculator_name,
            species=species,
        )
        progress({"completed": 0, "total": 3, "message": "displacements"})
        phonons = Phonons(
            atoms,
            calculator,
            supercell=tuple(supercell),
            delta=delta,
            name=str(root / "phonon"),
        )
        phonons.run()
        if should_stop():
            return {"status": "cancelled"}
        progress({"completed": 1, "total": 3, "message": "force constants"})
        phonons.read(acoustic=True)
        progress({"completed": 2, "total": 3, "message": "dos"})
        raw = phonons.get_dos(kpts=tuple(kpts))
        grid = raw.sample_grid(npts=npts, width=1e-3)
        omega = grid.get_energies()
        dos = grid.get_weights()
        dos_path = root / "phonon_dos.csv"
        rows = ["omega_eV,dos"]
        rows.extend(f"{float(w)},{float(d)}" for w, d in zip(omega, dos))
        dos_path.write_text("\n".join(rows), encoding="utf-8")
        positive = [float(w) for w in omega if w > 0]
        progress({"completed": 3, "total": 3, "message": "finished"})
        return {
            "n_modes": int(len(omega)),
            "omega_min_eV": float(np.min(omega)),
            "omega_max_eV": float(np.max(omega)),
            "n_imaginary": int(np.sum(np.asarray(omega) < -1e-4)),
            "dos_filepath": str(dos_path.absolute()),
            "calculator_requested": calculator_name,
            "calculator_used": calculator_used,
            "calculator_fallbacks": calculator_errors,
            "positive_mode_count": len(positive),
        }

    record = STORE.submit("phonon", _runner, params=params, job_id=job_id)
    record["next_action"] = f"Call get_job with job_id={record['job_id']} until status is completed or failed."
    return record
