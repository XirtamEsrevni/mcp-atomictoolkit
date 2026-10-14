"""Simple substitutional defect. Fits Render."""

from __future__ import annotations

from typing import Dict, Optional

from ase.io import read, write


def substitute_atom(
    input_filepath: str,
    output_filepath: str,
    index: int,
    new_symbol: str,
    input_format: Optional[str] = None,
    output_format: Optional[str] = None,
) -> Dict:
    """Replace the atom at index with new_symbol and write the result."""
    if not new_symbol or not new_symbol.strip():
        raise ValueError("new_symbol is required")
    atoms = read(input_filepath, format=input_format)
    if index < 0 or index >= len(atoms):
        raise ValueError(f"index {index} out of range for {len(atoms)} atoms")
    old = atoms[index].symbol
    atoms[index].symbol = new_symbol.strip()
    write(output_filepath, atoms, format=output_format)
    return {
        "output_filepath": output_filepath,
        "index": index,
        "old_symbol": old,
        "new_symbol": new_symbol.strip(),
        "formula": atoms.get_chemical_formula(),
        "n_atoms": len(atoms),
    }
