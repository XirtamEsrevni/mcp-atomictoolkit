"""Tests for trajectory thermodynamics."""

from pathlib import Path

import numpy as np
from ase.build import bulk
from ase.calculators.emt import EMT
from ase.io import write
from ase.md.velocitydistribution import MaxwellBoltzmannDistribution

from mcp_atomictoolkit.analysis.thermodynamics import trajectory_thermodynamics


def test_trajectory_thermodynamics_emt(tmp_path):
    atoms = bulk("Cu", "fcc", a=3.6) * (2, 2, 2)
    atoms.calc = EMT()
    MaxwellBoltzmannDistribution(atoms, temperature_K=300)
    from ase.calculators.singlepoint import SinglePointCalculator
    frames = []
    for _ in range(5):
        e = atoms.get_potential_energy()
        f = atoms.get_forces()
        frame = atoms.copy()
        frame.calc = SinglePointCalculator(frame, energy=e, forces=f)
        frames.append(frame)
        atoms.positions += 0.01 * np.random.randn(*atoms.positions.shape)

    path = tmp_path / "traj.extxyz"
    write(path, frames, format="extxyz")

    result = trajectory_thermodynamics(str(path))
    assert result["n_frames"] == 5
    assert result["n_atoms"] == 8
    assert "energy_eV" in result
    assert result["energy_eV"]["mean"] == result["energy_eV"]["mean"]
    assert "max_force_eV_per_A" in result


def test_thermodynamics_skips_frames(tmp_path):
    atoms = bulk("Cu", "fcc", a=3.6)
    atoms.calc = EMT()
    frames = [atoms.copy() for _ in range(4)]
    path = tmp_path / "t.extxyz"
    write(path, frames)
    result = trajectory_thermodynamics(str(path), skip_frames=2)
    assert result["n_frames"] == 2
