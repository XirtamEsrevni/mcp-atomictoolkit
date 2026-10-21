"""Lightweight Buckingham parameter fit from reference energies.

Buckingham is a common analytical pair potential: A*exp(-r/rho) - C/r**6.
It ships with no extra dependencies beyond ASE/numpy and fits the Render
memory limit. This fits A, rho, and C against reference energies and
registers the result as a runtime calculator.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional, Sequence

import numpy as np
from ase import Atoms
from ase.calculators.calculator import Calculator, all_changes
from ase.io import read
from ase.neighborlist import NeighborList

from mcp_atomictoolkit.calculator_registry import register_calculator


class BuckinghamPotential(Calculator):
    """Simple Buckingham pair potential with cutoff.

    V(r) = A * exp(-r / rho) - C / r**6   for r < rc
    """

    implemented_properties = ["energy", "forces"]

    def __init__(self, A: float, rho: float, C: float, rc: float = 10.0, **kwargs):
        super().__init__(**kwargs)
        self.A = float(A)
        self.rho = float(rho)
        self.C = float(C)
        self.rc = float(rc)

    def calculate(self, atoms=None, properties=("energy", "forces"), system_changes=all_changes):
        super().calculate(atoms, properties, system_changes)
        atoms = self.atoms
        n = len(atoms)
        energy = 0.0
        forces = np.zeros((n, 3))

        # Neighbor list with cutoff
        cutoffs = [self.rc / 2.0] * n
        nl = NeighborList(cutoffs, self_interaction=False, bothways=True)
        nl.update(atoms)

        for i in range(n):
            indices, offsets = nl.get_neighbors(i)
            for j, offset in zip(indices, offsets):
                if j < i:  # avoid double-counting
                    continue
                dvec = atoms.positions[j] + np.dot(offset, atoms.cell) - atoms.positions[i]
                r = np.linalg.norm(dvec)
                if r < 1e-6 or r >= self.rc:
                    continue
                # Energy contribution
                exp_term = np.exp(-r / self.rho)
                inv_r6 = 1.0 / (r ** 6)
                vij = self.A * exp_term - self.C * inv_r6
                energy += vij

                # Force on i from this pair: -dV/dr * rhat
                # dV/dr = A * (-1/rho) * exp + 6 * C / r**7
                dVdr = -(self.A / self.rho) * exp_term + 6.0 * self.C / (r ** 7)
                rhat = dvec / r
                f = -dVdr * rhat
                forces[i] += f
                forces[j] -= f

        self.results["energy"] = energy
        self.results["forces"] = forces


def _buckingham_energy(atoms_list: Sequence[Atoms], A: float, rho: float, C: float, rc: float = 10.0) -> np.ndarray:
    energies = []
    calc = BuckinghamPotential(A=A, rho=rho, C=C, rc=rc)
    for atoms in atoms_list:
        a = atoms.copy()
        a.calc = calc
        energies.append(float(a.get_potential_energy()))
    return np.asarray(energies)


def fit_buckingham_from_structures(
    input_paths: Sequence[str],
    reference_energies: Sequence[float],
    name: str = "fitted_buckingham",
    input_format: Optional[str] = None,
    rc: float = 10.0,
) -> Dict:
    """Fit Buckingham parameters (A, rho, C) and register the calculator."""
    if len(input_paths) == 0:
        raise ValueError("input_paths is empty")
    structures = []
    for path in input_paths:
        frames = read(path, format=input_format, index=":")
        if not isinstance(frames, list):
            frames = [frames]
        structures.extend(frames)
    if len(structures) != len(reference_energies):
        raise ValueError(
            f"Got {len(structures)} structures but {len(reference_energies)} energies"
        )
    targets = np.asarray(reference_energies, dtype=float)

    # Coarse grid to seed, then local refine. Parameter ranges are typical for metals.
    best = {"loss": float("inf"), "A": 1000.0, "rho": 0.3, "C": 50.0}
    for A in np.linspace(100.0, 5000.0, 6):
        for rho in np.linspace(0.15, 0.45, 5):
            for C in np.linspace(10.0, 200.0, 5):
                try:
                    pred = _buckingham_energy(structures, float(A), float(rho), float(C), rc)
                except Exception:
                    continue
                loss = float(np.mean((pred - targets) ** 2))
                if loss < best["loss"]:
                    best = {"loss": loss, "A": float(A), "rho": float(rho), "C": float(C)}

    from scipy.optimize import minimize

    def objective(x):
        A, rho, C = map(float, x)
        if A <= 0 or rho <= 0 or C < 0:
            return 1e6
        try:
            pred = _buckingham_energy(structures, A, rho, C, rc)
        except Exception:
            return 1e6
        return float(np.mean((pred - targets) ** 2))

    opt = minimize(
        objective,
        x0=[best["A"], best["rho"], best["C"]],
        method="Nelder-Mead",
        options={"xatol": 1e-3, "fatol": 1e-6, "maxiter": 120},
    )
    A = float(opt.x[0])
    rho = float(opt.x[1])
    C = float(opt.x[2])
    best["loss"] = float(opt.fun)

    def factory():
        return BuckinghamPotential(A=A, rho=rho, C=C, rc=rc)

    register_calculator(name, factory)

    result = {
        "name": name,
        "A_eV": A,
        "rho_Angstrom": rho,
        "C_eV_Angstrom6": C,
        "rc_Angstrom": rc,
        "rmse_eV": float(np.sqrt(best["loss"])),
        "n_structures": len(structures),
        "registered": True,
    }
    return result


def fit_buckingham_and_save(
    input_paths: Sequence[str],
    reference_energies: Sequence[float],
    output_path: str,
    name: str = "fitted_buckingham",
    **kwargs,
) -> Dict:
    """Fit and also write the parameters to a JSON artifact."""
    result = fit_buckingham_from_structures(
        input_paths=input_paths,
        reference_energies=reference_energies,
        name=name,
        **kwargs,
    )
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    result["artifact"] = str(path)
    return result
