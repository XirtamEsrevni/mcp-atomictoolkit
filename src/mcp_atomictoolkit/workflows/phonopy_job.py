"""Optional phonopy phonon DOS. Disabled on Render; requires phonopy."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional, Sequence
from uuid import uuid4

import numpy as np
from ase.io import read

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


def submit_phonopy_job(
    input_filepath: str,
    calculator_name: str = "emt",
    supercell: Optional[Sequence[int]] = None,
    displacement: float = 0.01,
    input_format: Optional[str] = None,
) -> Dict:
    """Start a phonopy finite-displacement phonon job. Poll get_job.

    Requires the optional phonopy package. Disabled on Render.
    """
    if _render_blocked():
        raise ValueError("Phonopy is disabled on the Render memory profile.")
    try:
        import phonopy  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "phonopy is not installed. Install with `pip install phonopy` "
            "or `pip install -e '.[phonopy]'`."
        ) from exc

    supercell = [int(v) for v in (supercell or [1, 1, 1])]
    if any(v < 1 for v in supercell):
        raise ValueError("supercell values must be at least 1")
    if int(np.prod(supercell)) > 4:
        raise ValueError("supercell product must be 4 or fewer for this job")

    job_id = uuid4().hex[:12]
    out_dir = Path(os.environ.get("JOBS_DIR", "jobs")) / job_id
    out_dir.mkdir(parents=True, exist_ok=True)

    def _runner(bound_job_id, progress, should_stop):
        from phonopy import Phonopy
        from phonopy.structure.atoms import PhonopyAtoms

        root = Path(os.environ.get("JOBS_DIR", "jobs")) / bound_job_id
        root.mkdir(parents=True, exist_ok=True)
        if should_stop():
            return {"status": "cancelled"}

        atoms = read(input_filepath, format=input_format)
        species = sorted(set(atoms.get_chemical_symbols()))
        calculator, used, errors = resolve_calculator(calculator_name, species=species)

        progress({"completed": 0, "total": 3, "message": "displacements"})
        unitcell = PhonopyAtoms(
            symbols=atoms.get_chemical_symbols(),
            cell=atoms.cell.array,
            positions=atoms.get_positions(),
        )
        phonon = Phonopy(unitcell, supercell_matrix=np.diag(supercell))
        phonon.generate_displacements(distance=displacement)
        supercells = phonon.supercells_with_displacements

        progress({"completed": 1, "total": 3, "message": "forces"})
        forces = []
        for sc in supercells:
            if sc is None:
                continue
            a = atoms.copy()
            a.set_cell(sc.cell, scale_atoms=False)
            a.set_positions(sc.positions)
            a.calc = calculator
            forces.append(a.get_forces())
        phonon.forces = forces

        if should_stop():
            return {"status": "cancelled"}

        progress({"completed": 2, "total": 3, "message": "dos"})
        phonon.produce_force_constants()
        mesh = [8, 8, 8]
        phonon.run_mesh(mesh)
        phonon.run_total_dos()
        dos = phonon.get_total_dos_dict()

        csv_path = root / "phonopy_dos.csv"
        rows = ["frequency_THz,dos"]
        for f, d in zip(dos["frequency_points"], dos["total_dos"]):
            rows.append(f"{float(f)},{float(d)}")
        csv_path.write_text("\n".join(rows), encoding="utf-8")

        progress({"completed": 3, "total": 3, "message": "finished"})
        return {
            "calculator_used": used,
            "calculator_errors": errors,
            "n_displacements": len(forces),
            "dos_filepath": str(csv_path),
        }

    params = {
        "input_filepath": input_filepath,
        "calculator_name": calculator_name,
        "supercell": supercell,
    }
    record = STORE.submit("phonopy", _runner, params=params, job_id=job_id)
    record["next_action"] = f"Call get_job with job_id={record['job_id']} until status is completed or failed."
    return record
