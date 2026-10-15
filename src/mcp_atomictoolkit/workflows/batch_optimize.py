"""Batch geometry optimization with a step cap. Fits small lists on Render."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Sequence

from ase.io import read, write
from ase.optimize import BFGS

from mcp_atomictoolkit.calculators import resolve_calculator


def batch_optimize(
    input_paths: Sequence[str],
    output_dir: str,
    calculator_name: str = "auto",
    max_steps: int = 20,
    fmax: float = 0.1,
    input_format: Optional[str] = None,
    max_structures: int = 10,
) -> Dict:
    """Relax each structure with a hard step cap and write the results.

    Default limits (10 structures, 20 steps) keep it safe on Render.
    """
    if not input_paths:
        raise ValueError("input_paths is empty")
    if len(input_paths) > max_structures:
        raise ValueError(
            f"Batch limited to {max_structures} structures. "
            "Split the list or raise max_structures off-Render."
        )
    if max_steps < 1:
        raise ValueError("max_steps must be at least 1")
    if fmax <= 0:
        raise ValueError("fmax must be positive")

    out_root = Path(output_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    results: List[Dict] = []
    for i, path in enumerate(input_paths):
        atoms = read(path, format=input_format)
        species = sorted(set(atoms.get_chemical_symbols()))
        calculator, used, errors = resolve_calculator(calculator_name, species=species)
        atoms.calc = calculator

        opt = BFGS(atoms, logfile=None)
        converged = opt.run(fmax=fmax, steps=max_steps)

        out_path = out_root / f"relaxed_{i:03d}.extxyz"
        write(out_path, atoms, format="extxyz")

        energy = float(atoms.get_potential_energy())
        results.append(
            {
                "input": path,
                "output": str(out_path),
                "formula": atoms.get_chemical_formula(),
                "n_atoms": len(atoms),
                "converged": bool(converged),
                "steps": int(opt.nsteps),
                "energy_eV": energy,
                "calculator_used": used,
                "calculator_errors": errors,
            }
        )

    return {
        "n_structures": len(results),
        "output_dir": str(out_root),
        "results": results,
        "n_converged": sum(1 for r in results if r["converged"]),
    }
