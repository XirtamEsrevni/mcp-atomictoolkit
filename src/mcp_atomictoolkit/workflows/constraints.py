"""Fixed-atom constraints for optimization and MD. Fits Render."""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from ase.constraints import FixAtoms
from ase.io import read, write


def apply_fixed_atoms(
    input_filepath: str,
    output_filepath: str,
    indices: Sequence[int],
    input_format: Optional[str] = None,
    output_format: Optional[str] = None,
) -> Dict:
    """Write a structure with FixAtoms applied to the given indices.

    The constraint is stored in the output file (extxyz/cif where supported)
    so later optimize/MD tools pick it up.
    """
    if not indices:
        raise ValueError("indices is empty")
    atoms = read(input_filepath, format=input_format)
    bad = [i for i in indices if i < 0 or i >= len(atoms)]
    if bad:
        raise ValueError(f"indices out of range: {bad}")
    atoms.set_constraint(FixAtoms(indices=list(indices)))
    write(output_filepath, atoms, format=output_format)
    return {
        "output_filepath": output_filepath,
        "n_atoms": len(atoms),
        "n_fixed": len(indices),
        "fixed_indices": list(indices),
        "formula": atoms.get_chemical_formula(),
    }
