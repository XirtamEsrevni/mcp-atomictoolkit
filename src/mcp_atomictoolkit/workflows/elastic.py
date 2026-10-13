"""Full Voigt elastic tensor from finite strains."""

from __future__ import annotations

from typing import Dict, Optional, Sequence

import numpy as np
from ase.io import read

from mcp_atomictoolkit.calculators import resolve_calculator

# Six independent Voigt strain modes (xx, yy, zz, yz, xz, xy)
_VOIGT_MODES = (
    (0, 0),
    (1, 1),
    (2, 2),
    (1, 2),
    (0, 2),
    (0, 1),
)


def compute_elastic_tensor(
    input_filepath: str,
    calculator_name: str = "auto",
    strain: float = 0.005,
    input_format: Optional[str] = None,
) -> Dict:
    """Compute the 6x6 Voigt elastic tensor (GPa) and derived moduli.

    Applies small symmetric strains, measures stress, and fits Cij.
    Suitable for small cells; for large systems prefer a background job.
    """
    if strain <= 0 or strain > 0.05:
        raise ValueError("strain must be in (0, 0.05]")
    atoms0 = read(input_filepath, format=input_format)
    species = sorted(set(atoms0.get_chemical_symbols()))
    calculator, used, errors = resolve_calculator(calculator_name, species=species)

    # Reference stress
    atoms0.calc = calculator
    stress0 = np.asarray(atoms0.get_stress(voigt=True), dtype=float)

    cij = np.zeros((6, 6), dtype=float)
    for col, (i, j) in enumerate(_VOIGT_MODES):
        # Positive and negative strain for central difference
        for sign in (+1.0, -1.0):
            atoms = atoms0.copy()
            cell = atoms.cell.array.copy()
            # Apply symmetric strain
            strain_tensor = np.zeros((3, 3))
            strain_tensor[i, j] = sign * strain
            strain_tensor[j, i] = sign * strain
            if i != j:
                # Voigt shear convention: engineering strain is 2*eps
                strain_tensor[i, j] *= 0.5
                strain_tensor[j, i] *= 0.5
            atoms.set_cell(cell @ (np.eye(3) + strain_tensor), scale_atoms=True)
            atoms.calc = calculator
            stress = np.asarray(atoms.get_stress(voigt=True), dtype=float)
            delta = stress - stress0
            # Accumulate; divide by 2*strain later
            cij[:, col] += sign * delta

    # Central difference: (s(+e) - s(-e)) / (2e) = C
    cij /= 2.0 * strain
    # ASE stress is in eV/Å³; convert to GPa (1 eV/Å³ ≈ 160.21766208 GPa)
    ev_per_a3_to_gpa = 160.21766208
    cij_gpa = cij * ev_per_a3_to_gpa

    # Derived isotropic averages (Voigt)
    c11 = cij_gpa[0, 0]
    c12 = cij_gpa[0, 1]
    c44 = cij_gpa[3, 3]
    bulk = (c11 + 2 * c12) / 3.0
    shear = (c11 - c12 + 3 * c44) / 5.0
    # Guard against singular
    if abs(3 * bulk + shear) < 1e-8:
        young = float("nan")
        poisson = float("nan")
    else:
        young = 9 * bulk * shear / (3 * bulk + shear)
        poisson = (3 * bulk - 2 * shear) / (2 * (3 * bulk + shear))

    return {
        "calculator_used": used,
        "calculator_errors": errors,
        "strain": float(strain),
        "cij_GPa": cij_gpa.tolist(),
        "bulk_modulus_GPa": float(bulk),
        "shear_modulus_GPa": float(shear),
        "young_modulus_GPa": float(young),
        "poisson_ratio": float(poisson),
    }
