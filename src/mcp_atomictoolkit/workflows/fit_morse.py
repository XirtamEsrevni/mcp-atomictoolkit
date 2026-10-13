"""Lightweight Morse parameter fit from reference energies.

Morse ships with ASE and fits the Render memory limit. This fits D, r0, and alpha
against reference energies and registers the result as a runtime calculator.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional, Sequence

import numpy as np
from ase.calculators.morse import MorsePotential
from ase.io import read

from mcp_atomictoolkit.calculator_registry import register_calculator


def _morse_energy(atoms_list, D: float, r0: float, alpha: float) -> np.ndarray:
    energies = []
    calc = MorsePotential(epsilon=D, r0=r0, rho0=alpha)
    for atoms in atoms_list:
        a = atoms.copy()
        a.calc = calc
        energies.append(float(a.get_potential_energy()))
    return np.asarray(energies)


def fit_morse_from_structures(
    input_paths: Sequence[str],
    reference_energies: Sequence[float],
    name: str = "fitted_morse",
    input_format: Optional[str] = None,
) -> Dict:
    """Fit Morse parameters and register the calculator."""
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

    # Grid seed then local refine
    best = {"loss": float("inf"), "D": 0.5, "r0": 2.5, "alpha": 1.5}
    for D in np.linspace(0.1, 2.0, 6):
        for r0 in np.linspace(1.8, 3.5, 6):
            for alpha in np.linspace(0.8, 2.5, 5):
                try:
                    pred = _morse_energy(structures, float(D), float(r0), float(alpha))
                except Exception:
                    continue
                loss = float(np.mean((pred - targets) ** 2))
                if loss < best["loss"]:
                    best = {"loss": loss, "D": float(D), "r0": float(r0), "alpha": float(alpha)}

    from scipy.optimize import minimize

    def objective(x):
        D, r0, alpha = map(float, x)
        if D <= 0 or r0 <= 0 or alpha <= 0:
            return 1e6
        try:
            pred = _morse_energy(structures, D, r0, alpha)
        except Exception:
            return 1e6
        return float(np.mean((pred - targets) ** 2))

    opt = minimize(
        objective,
        x0=[best["D"], best["r0"], best["alpha"]],
        method="Nelder-Mead",
        options={"xatol": 1e-3, "fatol": 1e-5, "maxiter": 100},
    )
    D, r0, alpha = map(float, opt.x)
    loss = float(opt.fun)

    def factory():
        return MorsePotential(epsilon=D, r0=r0, rho0=alpha)

    register_calculator(name, factory)
    return {
        "name": name,
        "D_eV": D,
        "r0_Angstrom": r0,
        "alpha_per_Angstrom": alpha,
        "rmse_eV": float(np.sqrt(loss)),
        "n_structures": len(structures),
        "registered": True,
    }


def fit_morse_and_save(
    input_paths: Sequence[str],
    reference_energies: Sequence[float],
    output_path: str,
    name: str = "fitted_morse",
    **kwargs,
) -> Dict:
    result = fit_morse_from_structures(
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
