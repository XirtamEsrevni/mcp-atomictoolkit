"""Tests for Render expansion: Morse fit and light calculator resolution."""

from pathlib import Path

from ase.build import bulk
from ase.calculators.morse import MorsePotential
from ase.io import write

from mcp_atomictoolkit.calculators import resolve_calculator
from mcp_atomictoolkit.workflows.fit_morse import fit_morse_and_save


def test_morse_resolves_on_render(monkeypatch):
    monkeypatch.setenv("MEMORY_PROFILE", "render")
    calc, used, errors = resolve_calculator("morse", species=["Fe"])
    assert used == "morse"
    atoms = bulk("Fe", "bcc", a=2.8)
    atoms.calc = calc
    e = atoms.get_potential_energy()
    assert e == e


def test_fit_morse_registers(tmp_path):
    true_D, true_r0, true_alpha = 0.5, 2.5, 1.5
    structures = []
    energies = []
    for a in (3.4, 3.6, 3.8, 4.0):
        atoms = bulk("Cu", "fcc", a=a)
        atoms.calc = MorsePotential(epsilon=true_D, r0=true_r0, rho0=true_alpha)
        structures.append(atoms)
        energies.append(atoms.get_potential_energy())

    paths = []
    for i, atoms in enumerate(structures):
        p = tmp_path / f"s{i}.cif"
        write(p, atoms)
        paths.append(str(p))

    out = tmp_path / "morse.json"
    result = fit_morse_and_save(
        input_paths=paths,
        reference_energies=energies,
        output_path=str(out),
        name="test_morse",
    )
    assert out.exists()
    assert result["registered"] is True
    assert result["rmse_eV"] < 0.1

    calc, used, _ = resolve_calculator("test_morse", species=["Cu"])
    assert used == "test_morse"
    atoms = bulk("Cu", "fcc", a=3.6)
    atoms.calc = calc
    e = atoms.get_potential_energy()
    assert e == e
