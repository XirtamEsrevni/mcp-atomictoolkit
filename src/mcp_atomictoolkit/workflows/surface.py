"""Surface energy from a bulk reference and a symmetric slab."""

from __future__ import annotations

import os
from typing import Dict, Optional, Sequence

import numpy as np
from ase.build import bulk, surface

from mcp_atomictoolkit.calculators import resolve_calculator


def _render_limited() -> bool:
    explicit = os.environ.get("MEMORY_PROFILE", "").strip().lower()
    if explicit in {"full", "off", "disabled"}:
        return False
    if explicit in {"render", "lite", "free", "low"}:
        return True
    return os.environ.get("RENDER", "").strip().lower() in {"1", "true", "yes", "on"} or bool(
        os.environ.get("RENDER_SERVICE_ID")
    )


def surface_energy_workflow(
    formula: str = "Cu",
    crystal_system: str = "fcc",
    lattice_constant: float = 3.6,
    miller: Optional[Sequence[int]] = None,
    size: Optional[Sequence[int]] = None,
    layers: int = 3,
    vacuum: float = 8.0,
    calculator_name: str = "auto",
) -> Dict:
    """Return unrelaxed surface energy in J/m^2.

    gamma = (E_slab - N_slab * E_bulk_per_atom) / (2 A)
    """
    miller = list(miller or [1, 1, 1])
    size = list(size or [2, 2, 1])
    if len(miller) != 3 or len(size) != 3:
        raise ValueError("miller and size must each have 3 integers")
    n_atoms = int(np.prod(size) * layers)
    if _render_limited() and (n_atoms > 32 or layers > 4):
        raise ValueError(
            f"Surface cell would have {n_atoms} atoms. Render allows at most 32 atoms and 4 layers."
        )

    bulk_atoms = bulk(formula, crystal_system, a=lattice_constant)
    slab = surface(bulk_atoms, miller, layers, vacuum=vacuum)
    slab *= tuple(size)
    species = sorted(set(slab.get_chemical_symbols()))
    calculator, calculator_used, calculator_errors = resolve_calculator(
        calculator_name,
        species=species,
    )
    bulk_atoms.calc = calculator
    bulk_energy = float(bulk_atoms.get_potential_energy())
    energy_per_atom = bulk_energy / len(bulk_atoms)

    slab.calc = calculator
    slab_energy = float(slab.get_potential_energy())
    area = float(np.linalg.norm(np.cross(slab.cell[0], slab.cell[1])))
    excess = slab_energy - len(slab) * energy_per_atom
    gamma_eV_A2 = excess / (2.0 * area)
    # 1 eV/Å^2 = 16.02176634 J/m^2
    gamma_J_m2 = float(gamma_eV_A2 * 16.02176634)
    return {
        "formula": formula,
        "miller": miller,
        "layers": layers,
        "size": size,
        "n_slab_atoms": len(slab),
        "n_bulk_atoms": len(bulk_atoms),
        "area_A2": area,
        "bulk_energy_eV": bulk_energy,
        "slab_energy_eV": slab_energy,
        "surface_energy_J_m2": gamma_J_m2,
        "calculator_requested": calculator_name,
        "calculator_used": calculator_used,
        "calculator_fallbacks": calculator_errors,
        "method": "unrelaxed (E_slab - N E_bulk) / 2A",
    }
