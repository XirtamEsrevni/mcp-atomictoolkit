"""Structure comparison utilities. Lightweight and Render-friendly."""

from __future__ import annotations

from typing import Dict, Optional

import numpy as np
from ase.io import read
from ase.geometry import find_mic


def structure_rmsd(
    reference_filepath: str,
    target_filepath: str,
    reference_format: Optional[str] = None,
    target_format: Optional[str] = None,
    align: bool = True,
) -> Dict:
    """Compute RMSD between two structures after optional rigid alignment.

    Uses the Kabsch algorithm when align=True. Works for equal atom counts.
    Suitable for the Render memory limit.
    """
    ref = read(reference_filepath, format=reference_format)
    tgt = read(target_filepath, format=target_format)

    if len(ref) != len(tgt):
        raise ValueError(f"Atom count mismatch: {len(ref)} vs {len(tgt)}")
    if not np.array_equal(ref.numbers, tgt.numbers):
        raise ValueError("Atomic numbers differ; structures are not comparable")

    # Work in fractional or Cartesian with MIC for periodic
    ref_pos = ref.get_positions()
    tgt_pos = tgt.get_positions()

    # Center both
    ref_c = ref_pos - ref_pos.mean(axis=0)
    tgt_c = tgt_pos - tgt_pos.mean(axis=0)

    if align:
        # Kabsch
        cov = tgt_c.T @ ref_c
        u, _, vt = np.linalg.svd(cov)
        rot = vt.T @ u.T
        if np.linalg.det(rot) < 0:
            vt[-1, :] *= -1
            rot = vt.T @ u.T
        tgt_c = tgt_c @ rot

    diff = tgt_c - ref_c
    rmsd = float(np.sqrt(np.mean(np.sum(diff**2, axis=1))))
    max_disp = float(np.max(np.linalg.norm(diff, axis=1)))

    return {
        "n_atoms": len(ref),
        "rmsd_Angstrom": rmsd,
        "max_displacement_Angstrom": max_disp,
        "aligned": align,
        "formula": ref.get_chemical_formula(),
    }
