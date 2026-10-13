"""Finite-displacement phonon band structure as a background job."""

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


def submit_phonon_bands_job(
    input_filepath: str,
    calculator_name: str = "emt",
    supercell: Optional[Sequence[int]] = None,
    delta: float = 0.01,
    npoints: int = 20,
    input_format: Optional[str] = None,
) -> Dict:
    """Start a finite-displacement phonon band structure. Poll get_job. Disabled on Render."""
    if _render_blocked():
        raise ValueError("Phonon bands are disabled on the Render memory profile.")
    supercell = [int(v) for v in (supercell or [1, 1, 1])]
    if any(v < 1 for v in supercell):
        raise ValueError("supercell values must be at least 1")
    if int(np.prod(supercell)) > 4:
        raise ValueError("supercell product must be 4 or fewer for this phonon job")
    if npoints < 2:
        raise ValueError("npoints must be at least 2")

    job_id = uuid4().hex[:12]
    out_dir = Path(os.environ.get("JOBS_DIR", "jobs")) / job_id
    out_dir.mkdir(parents=True, exist_ok=True)

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

        progress({"completed": 2, "total": 3, "message": "bands"})
        # Use the lattice's standard high-symmetry path
        lat = atoms.cell.get_bravais_lattice()
        path = lat.bandpath(npoints=npoints)

        bs = phonons.get_band_structure(path)
        # bs.energies is list of arrays (spin, k, band) or similar
        energies = np.asarray(bs.energies)
        # Flatten to (nk, nbands)
        if energies.ndim == 3:
            energies = energies[0]
        kpts = path.kpts
        csv_path = root / "phonon_bands.csv"
        rows = ["k_index,k_dist,band,omega_eV"]
        # Approximate cumulative distance
        dists = np.zeros(len(kpts))
        for i in range(1, len(kpts)):
            dists[i] = dists[i - 1] + np.linalg.norm(kpts[i] - kpts[i - 1])
        for ik in range(energies.shape[0]):
            for ib in range(energies.shape[1]):
                rows.append(f"{ik},{dists[ik]:.6f},{ib},{float(energies[ik, ib]):.6f}")
        csv_path.write_text("\n".join(rows), encoding="utf-8")

        # Simple plot
        try:
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=(6, 4))
            for ib in range(energies.shape[1]):
                ax.plot(dists, energies[:, ib], "b-", lw=0.8)
            ax.axhline(0, color="k", lw=0.5)
            ax.set_xlabel("k-distance")
            ax.set_ylabel("ω (eV)")
            ax.set_title("Phonon bands")
            png_path = root / "phonon_bands.png"
            fig.tight_layout()
            fig.savefig(png_path, dpi=100)
            plt.close(fig)
        except Exception:
            png_path = None

        progress({"completed": 3, "total": 3, "message": "finished"})
        return {
            "calculator_used": calculator_used,
            "calculator_errors": calculator_errors,
            "n_kpoints": int(energies.shape[0]),
            "n_bands": int(energies.shape[1]),
            "omega_min_eV": float(np.min(energies)),
            "omega_max_eV": float(np.max(energies)),
            "outputs": {
                "bands_csv": str(csv_path),
                "bands_png": str(png_path) if png_path else None,
            },
        }

    params = {
        "input_filepath": input_filepath,
        "calculator_name": calculator_name,
        "supercell": supercell,
        "npoints": npoints,
        "outputs": {"bands": str(out_dir / "phonon_bands.csv")},
    }
    record = STORE.submit("phonon_bands", _runner, params=params, job_id=job_id)
    record["next_action"] = f"Call get_job with job_id={record['job_id']} until status is completed or failed."
    return record
