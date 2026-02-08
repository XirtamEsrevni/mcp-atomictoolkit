"""Structure optimization using MLIPs (KIM, Orb, and Nequix)."""

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from ase import Atoms
from ase.constraints import FixAtoms, FixBondLength, FixBondLengths
from ase.optimize import BFGS

from mcp_atomictoolkit.calculators import DEFAULT_CALCULATOR_NAME, resolve_calculator


def apply_constraints(atoms: Atoms, constraints: Optional[Dict[str, Any]]) -> None:
    """Apply ASE constraints (fixed atoms, fixed bonds, fixed cell metadata)."""
    if not constraints:
        return

    new_constraints: List[Any] = []

    fixed_atoms = constraints.get("fixed_atoms")
    if fixed_atoms:
        new_constraints.append(FixAtoms(indices=fixed_atoms))

    fixed_bonds = constraints.get("fixed_bonds") or constraints.get("bonds")
    if fixed_bonds:
        pairs: List[Tuple[int, int]] = []
        for bond in fixed_bonds:
            if isinstance(bond, dict):
                indices = bond.get("indices") or bond.get("pair")
                if indices is None:
                    indices = (bond.get("a"), bond.get("b"))
                pairs.append(tuple(indices))
            else:
                pairs.append(tuple(bond))
        if len(pairs) == 1:
            new_constraints.append(FixBondLength(*pairs[0]))
        else:
            new_constraints.append(FixBondLengths(pairs))

    if new_constraints:
        existing = atoms.constraints
        if existing:
            if not isinstance(existing, (list, tuple)):
                existing = [existing]
            new_constraints = list(existing) + new_constraints
        atoms.set_constraint(new_constraints)

    if "fixed_cell" in constraints:
        atoms.info["fixed_cell"] = bool(constraints["fixed_cell"])


def optimize_structure(
    structure: Atoms,
    calculator_name: str = DEFAULT_CALCULATOR_NAME,
    max_steps: int = 50,
    fmax: float = 0.1,
    constraints: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Atoms:
    """Optimize structure using specified MLIP.

    Args:
        structure: Input structure
        calculator_name: Type of MLIP ('auto', 'kim', 'nequix', or 'orb'). Defaults to auto.
        max_steps: Maximum optimization steps
        fmax: Force convergence criterion
        constraints: Constraint settings (fixed atoms/cell/bonds)
        **kwargs: Additional optimization parameters

    Returns:
        Optimized structure
    """
    # Create a copy to avoid modifying input
    atoms = structure.copy()
    apply_constraints(atoms, constraints)

    # Set up calculator
    species = sorted(set(atoms.get_chemical_symbols()))
    calculator, calculator_used, calculator_errors = resolve_calculator(
        calculator_name,
        species=species,
    )
    atoms.calc = calculator
    atoms.info["calculator_requested"] = calculator_name
    atoms.info["calculator_used"] = calculator_used
    if calculator_errors:
        atoms.info["calculator_fallbacks"] = calculator_errors

    optimizer = BFGS(
        atoms, maxstep=kwargs.get("maxstep", 0.04), alpha=kwargs.get("alpha", 70.0)
    )

    try:
        optimizer.run(fmax=fmax, steps=max_steps)
        converged = optimizer.converged()
        if converged:
            atoms.info["optimization_converged"] = True
            atoms.info["optimization_steps"] = optimizer.nsteps
            atoms.info["optimization_fmax"] = max(
                np.linalg.norm(atoms.get_forces(), axis=1)
            )
        else:
            atoms.info["optimization_converged"] = False
            atoms.info["optimization_steps"] = max_steps
            atoms.info["optimization_fmax"] = max(
                np.linalg.norm(atoms.get_forces(), axis=1)
            )
    except Exception as e:
        atoms.info["optimization_error"] = str(e)
        atoms.info["optimization_converged"] = False

    return atoms
