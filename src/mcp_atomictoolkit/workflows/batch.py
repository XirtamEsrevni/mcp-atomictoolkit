"""Batch single-point energies. Fits small lists on Render."""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from ase.io import read

from mcp_atomictoolkit.calculators import resolve_calculator


def batch_single_point(
    input_paths: Sequence[str],
    calculator_name: str = "auto",
    input_format: Optional[str] = None,
    max_structures: int = 20,
) -> Dict:
    """Compute single-point energy for each structure in the list.

    Limited to max_structures to stay safe on Render. Returns a list of
    per-structure results and a summary.
    """
    if len(input_paths) == 0:
        raise ValueError("input_paths is empty")
    if len(input_paths) > max_structures:
        raise ValueError(
            f"Batch limited to {max_structures} structures. "
            "Split the list or raise max_structures off-Render."
        )

    results: List[Dict] = []
    for path in input_paths:
        atoms = read(path, format=input_format)
        species = sorted(set(atoms.get_chemical_symbols()))
        calculator, used, errors = resolve_calculator(calculator_name, species=species)
        atoms.calc = calculator
        energy = float(atoms.get_potential_energy())
        results.append(
            {
                "path": path,
                "formula": atoms.get_chemical_formula(),
                "n_atoms": len(atoms),
                "energy_eV": energy,
                "energy_per_atom_eV": energy / len(atoms),
                "calculator_used": used,
                "calculator_errors": errors,
            }
        )

    energies = [r["energy_eV"] for r in results]
    return {
        "n_structures": len(results),
        "results": results,
        "energy_min_eV": min(energies),
        "energy_max_eV": max(energies),
        "energy_mean_eV": sum(energies) / len(energies),
    }
