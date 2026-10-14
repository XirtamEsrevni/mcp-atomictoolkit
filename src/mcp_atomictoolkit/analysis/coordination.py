"""Coordination and neighbor analysis. Lightweight, fits Render."""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
from ase.io import read
from ase.neighborlist import neighbor_list


def coordination_analysis(
    input_filepath: str,
    cutoff: float = 3.0,
    input_format: Optional[str] = None,
) -> Dict:
    """Per-atom coordination numbers and species-resolved averages.

    Uses ASE neighbor_list. Suitable for the Render memory limit.
    """
    if cutoff <= 0:
        raise ValueError("cutoff must be positive")
    atoms = read(input_filepath, format=input_format)
    i, j = neighbor_list("ij", atoms, cutoff)
    counts = np.bincount(i, minlength=len(atoms))
    symbols = atoms.get_chemical_symbols()

    per_atom: List[Dict] = []
    for idx, (sym, cn) in enumerate(zip(symbols, counts)):
        per_atom.append({"index": int(idx), "symbol": sym, "coordination": int(cn)})

    # Species averages
    by_species: Dict[str, List[int]] = {}
    for entry in per_atom:
        by_species.setdefault(entry["symbol"], []).append(entry["coordination"])
    species_avg = {
        sym: float(np.mean(vals)) for sym, vals in by_species.items()
    }

    return {
        "n_atoms": len(atoms),
        "cutoff_Angstrom": float(cutoff),
        "formula": atoms.get_chemical_formula(),
        "mean_coordination": float(np.mean(counts)) if len(counts) else 0.0,
        "max_coordination": int(np.max(counts)) if len(counts) else 0,
        "species_average_coordination": species_avg,
        "per_atom": per_atom,
    }
