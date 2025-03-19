"""Structure optimization using MLIPs (Orb and MACE)."""

import numpy as np
from ase import Atoms
from ase.optimize import BFGS
from orb_models.forcefield import pretrained
from orb_models.forcefield.calculator import ORBCalculator


def get_orb_calculator() -> ORBCalculator:
    """Initialize Orb calculator for given structure.

    Args:
        structure: Input structure

    Returns:
        Configured Orb calculator
    """
    orbff = pretrained.orb_v2(device="cpu")
    calculator = ORBCalculator(orbff, device="cpu")
    return calculator


def optimize_structure(
    structure: Atoms,
    mlip_type: str = "orb",
    max_steps: int = 50,
    fmax: float = 0.1,
    **kwargs,
) -> Atoms:
    """Optimize structure using specified MLIP.

    Args:
        structure: Input structure
        mlip_type: Type of MLIP ('orb' or 'mace')
        max_steps: Maximum optimization steps
        fmax: Force convergence criterion
        **kwargs: Additional optimization parameters

    Returns:
        Optimized structure
    """
    # Create a copy to avoid modifying input
    atoms = structure.copy()

    # Set up calculator
    if mlip_type.lower() == "orb":
        calculator = get_orb_calculator()
    else:
        raise ValueError(f"Unknown MLIP type: {mlip_type}")

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
