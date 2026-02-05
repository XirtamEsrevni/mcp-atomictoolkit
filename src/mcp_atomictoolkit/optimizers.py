"""Structure optimization using MLIPs (Orb and Nequix)."""

import os

from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

import numpy as np
from ase import Atoms
from ase.constraints import FixAtoms, FixBondLength, FixBondLengths
from ase.optimize import BFGS

if TYPE_CHECKING:
    from nequix.calculator import NequixCalculator
    from orb_models.forcefield.calculator import ORBCalculator

NEQUIX_DEFAULT_MODEL = "nequix-mp-1"
NEQUIX_DEFAULT_BACKEND = "jax"


def _configure_jax_for_cpu() -> None:
    """Avoid JAX GPU/TPU plugin probing in CPU-only runtimes."""
    os.environ.setdefault("JAX_PLATFORMS", "cpu")
    os.environ.setdefault("JAX_PLATFORM_NAME", "cpu")


def _normalize_calculator_name(calculator_name: str) -> str:
    """Return canonical calculator key, accepting common aliases/typos."""
    aliases = {
        "neqix": "nequix",
    }
    return aliases.get(calculator_name.lower(), calculator_name.lower())


def get_orb_calculator() -> "ORBCalculator":
    """Initialize Orb calculator."""
    from orb_models.forcefield import pretrained
    from orb_models.forcefield.calculator import ORBCalculator

    orbff = pretrained.orb_v2(device="cpu")
    calculator = ORBCalculator(orbff, device="cpu")
    return calculator


def get_nequix_calculator(
    model_name: str = NEQUIX_DEFAULT_MODEL,
    backend: str = NEQUIX_DEFAULT_BACKEND,
) -> "NequixCalculator":
    """Initialize Nequix calculator on CPU."""
    if backend == "jax":
        _configure_jax_for_cpu()

    from nequix.calculator import NequixCalculator

    return NequixCalculator(
        model_name,
        backend=backend,
    )


def get_calculator(calculator_name: str) -> "ORBCalculator | NequixCalculator":
    """Return an ASE calculator for the requested MLIP."""
    calculator_key = _normalize_calculator_name(calculator_name)
    if calculator_key == "orb":
        return get_orb_calculator()
    if calculator_key == "nequix":
        return get_nequix_calculator()
    raise ValueError(f"Unknown MLIP type: {calculator_name}")


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
    calculator_name: str = "nequix",
    max_steps: int = 50,
    fmax: float = 0.1,
    constraints: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Atoms:
    """Optimize structure using specified MLIP.

    Args:
        structure: Input structure
        calculator_name: Type of MLIP ('nequix' or 'orb')
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
    calculator = get_calculator(calculator_name)

    atoms.calc = calculator

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
