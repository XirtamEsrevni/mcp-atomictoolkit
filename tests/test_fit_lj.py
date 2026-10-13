"""Tests for the lightweight LJ fitting backend."""

from pathlib import Path

from ase.build import bulk
from ase.calculators.lj import LennardJones
from ase.io import write

from mcp_atomictoolkit.calculators import resolve_calculator
from mcp_atomictoolkit.workflows.fit_lj import fit_lj_and_save


def test_fit_lj_recovers_parameters(tmp_path):
    # Generate reference data from a known LJ
    true_eps, true_sig = 0.2, 2.5
    structures = []
    energies = []
    for a in (3.5, 3.7, 3.9, 4.1):
        atoms = bulk("Cu", "fcc", a=a)
        atoms.calc = LennardJones(epsilon=true_eps, sigma=true_sig, rc=10.0)
        structures.append(atoms)
        energies.append(atoms.get_potential_energy())

    paths = []
    for i, atoms in enumerate(structures):
        p = tmp_path / f"s{i}.cif"
        write(p, atoms)
        paths.append(str(p))

    out = tmp_path / "fit.json"
    result = fit_lj_and_save(
        input_paths=paths,
        reference_energies=energies,
        output_path=str(out),
        name="test_lj",
    )
    assert out.exists()
    assert result["registered"] is True
    assert result["rmse_eV"] < 0.05
    # Recovered parameters should be in the right ballpark
    assert abs(result["epsilon_eV"] - true_eps) < 0.1
    assert abs(result["sigma_Angstrom"] - true_sig) < 0.5

    calc, used, _ = resolve_calculator("test_lj", species=["Cu"])
    assert used == "test_lj"
    atoms = bulk("Cu", "fcc", a=3.6)
    atoms.calc = calc
    e = atoms.get_potential_energy()
    assert e == e  # finite
