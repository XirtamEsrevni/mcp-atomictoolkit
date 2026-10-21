"""Tests for the lightweight Buckingham fitting backend."""

from pathlib import Path

from ase.build import bulk
from ase.io import write

from mcp_atomictoolkit.calculators import resolve_calculator
from mcp_atomictoolkit.workflows.fit_buckingham import BuckinghamPotential, fit_buckingham_and_save


def test_fit_buckingham_recovers_energies(tmp_path):
    # Generate reference data from a known Buckingham
    true_A, true_rho, true_C = 2000.0, 0.28, 80.0
    structures = []
    energies = []
    for a in (3.5, 3.7, 3.9, 4.1, 4.3):
        atoms = bulk("Cu", "fcc", a=a)
        atoms.calc = BuckinghamPotential(A=true_A, rho=true_rho, C=true_C, rc=8.0)
        structures.append(atoms)
        energies.append(atoms.get_potential_energy())

    paths = []
    for i, atoms in enumerate(structures):
        p = tmp_path / f"s{i}.cif"
        write(p, atoms)
        paths.append(str(p))

    out = tmp_path / "fit.json"
    result = fit_buckingham_and_save(
        input_paths=paths,
        reference_energies=energies,
        output_path=str(out),
        name="test_buck",
        rc=8.0,
    )
    assert out.exists()
    assert result["registered"] is True
    assert result["rmse_eV"] < 0.05
    assert result["A_eV"] > 0
    assert result["rho_Angstrom"] > 0
    assert result["C_eV_Angstrom6"] >= 0

    calc, used, _ = resolve_calculator("test_buck", species=["Cu"])
    assert used == "test_buck"
    # Reproduce energies on the training structures
    for atoms, target in zip(structures, energies):
        a = atoms.copy()
        a.calc = calc
        pred = a.get_potential_energy()
        assert abs(pred - target) < 0.1
