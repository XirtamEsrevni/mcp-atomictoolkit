"""Lightweight Lennard-Jones parameter fit from reference energies.

First distillation slice: fit epsilon and sigma for a single-element LJ potential
against a set of structures with known energies, then register the result as a
runtime calculator.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np
from ase.io import read
from ase.calculators.lj import LennardJones

from mcp_atomictoolkit.calculator_registry import register_calculator


def _lj_energy(atoms_list: List, epsilon: float, sigma: float, rc: float) -> np.ndarray:
    energies = []
    calc = LennardJones(epsilon=epsilon, sigma=sigma, rc=rc)
    for atoms in atoms_list:
        a = atoms.copy()
        a.calc = calc
        energies.append(float(a.get_potential_energy()))
    return np.asarray(energies)


def fit_lj_from_structures(
    input_paths: Sequence[str],
    reference_energies: Sequence[float],
    name: str = "fitted_lj",
    sigma_guess: float = 2.5,
    epsilon_guess: float = 0.1,
    rc: float = 10.0,
    input_format: Optional[str] = None,
) -> Dict:
    """Fit LJ epsilon/sigma to reference energies and register the calculator.

    Parameters
    ----------
    input_paths:
        Paths to structure files (one structure each, or a single trajectory).
    reference_energies:
        Target potential energies (eV), one per structure.
    name:
        Name under which the fitted calculator is registered.
    """
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

    # Coarse grid to seed, then scipy local minimization.
    best = {"loss": float("inf"), "epsilon": epsilon_guess, "sigma": sigma_guess}
    for eps in np.linspace(0.01, 1.0, 8):
        for sig in np.linspace(1.8, 3.5, 8):
            try:
                pred = _lj_energy(structures, float(eps), float(sig), rc)
            except Exception:
                continue
            loss = float(np.mean((pred - targets) ** 2))
            if loss < best["loss"]:
                best = {"loss": loss, "epsilon": float(eps), "sigma": float(sig)}

    from scipy.optimize import minimize

    def objective(x):
        eps, sig = float(x[0]), float(x[1])
        if eps <= 0 or sig <= 0:
            return 1e6
        try:
            pred = _lj_energy(structures, eps, sig, rc)
        except Exception:
            return 1e6
        return float(np.mean((pred - targets) ** 2))

    opt = minimize(
        objective,
        x0=[best["epsilon"], best["sigma"]],
        method="Nelder-Mead",
        options={"xatol": 1e-4, "fatol": 1e-6, "maxiter": 80},
    )
    epsilon = float(opt.x[0])
    sigma = float(opt.x[1])
    best["loss"] = float(opt.fun)

    def factory():
        return LennardJones(epsilon=epsilon, sigma=sigma, rc=rc)

    register_calculator(name, factory)

    result = {
        "name": name,
        "epsilon_eV": epsilon,
        "sigma_Angstrom": sigma,
        "rc_Angstrom": rc,
        "rmse_eV": float(np.sqrt(best["loss"])),
        "n_structures": len(structures),
        "registered": True,
    }
    return result


def fit_lj_and_save(
    input_paths: Sequence[str],
    reference_energies: Sequence[float],
    output_path: str,
    name: str = "fitted_lj",
    **kwargs,
) -> Dict:
    """Fit and also write the parameters to a JSON artifact."""
    result = fit_lj_from_structures(
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
