"""Lightweight trajectory thermodynamics. Fits the Render memory limit."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import numpy as np
from ase.io import read


def trajectory_thermodynamics(
    input_filepath: str,
    input_format: Optional[str] = None,
    skip_frames: int = 0,
) -> Dict:
    """Compute average energy, forces, and stress from a trajectory.

    Works with any ASE-readable trajectory. No heavy dependencies.
    Suitable for the 512 MB Render image.
    """
    if skip_frames < 0:
        raise ValueError("skip_frames must be >= 0")

    frames = read(input_filepath, format=input_format, index=":")
    if not isinstance(frames, list):
        frames = [frames]
    if skip_frames:
        frames = frames[skip_frames:]
    if len(frames) == 0:
        raise ValueError("No frames left after skip_frames")

    energies = []
    max_forces = []
    pressures = []
    temperatures = []

    for atoms in frames:
        if atoms.calc is None:
            # Try to read stored results from the trajectory
            try:
                e = atoms.get_potential_energy()
                energies.append(float(e))
            except Exception:
                pass
            try:
                f = atoms.get_forces()
                max_forces.append(float(np.max(np.linalg.norm(f, axis=1))))
            except Exception:
                pass
            try:
                s = atoms.get_stress(voigt=False)
                # Hydrostatic pressure in eV/Å³ → GPa
                p = -np.trace(s) / 3.0 * 160.21766208
                pressures.append(float(p))
            except Exception:
                pass
        else:
            energies.append(float(atoms.get_potential_energy()))
            f = atoms.get_forces()
            max_forces.append(float(np.max(np.linalg.norm(f, axis=1))))
            try:
                s = atoms.get_stress(voigt=False)
                p = -np.trace(s) / 3.0 * 160.21766208
                pressures.append(float(p))
            except Exception:
                pass

        # Kinetic temperature if momenta present
        if atoms.get_momenta() is not None and np.any(atoms.get_momenta()):
            try:
                temperatures.append(float(atoms.get_temperature()))
            except Exception:
                pass

    result: Dict = {
        "n_frames": len(frames),
        "n_atoms": len(frames[0]) if frames else 0,
    }
    if energies:
        arr = np.asarray(energies)
        result["energy_eV"] = {
            "mean": float(arr.mean()),
            "std": float(arr.std()),
            "min": float(arr.min()),
            "max": float(arr.max()),
        }
    if max_forces:
        arr = np.asarray(max_forces)
        result["max_force_eV_per_A"] = {
            "mean": float(arr.mean()),
            "max": float(arr.max()),
        }
    if pressures:
        arr = np.asarray(pressures)
        result["pressure_GPa"] = {
            "mean": float(arr.mean()),
            "std": float(arr.std()),
        }
    if temperatures:
        arr = np.asarray(temperatures)
        result["temperature_K"] = {
            "mean": float(arr.mean()),
            "std": float(arr.std()),
        }
    return result
