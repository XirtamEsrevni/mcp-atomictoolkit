import pytest
from ase.build import bulk

from mcp_atomictoolkit.calculators import resolve_calculator, describe_calculator_workspace


def test_lj_and_morse_run_on_copper():
    atoms = bulk("Cu", "fcc", a=3.6)
    for name in ("lj", "morse"):
        calc, used, errors = resolve_calculator(name, species=["Cu"])
        atoms.calc = calc
        energy = atoms.get_potential_energy()
        assert used == name
        assert errors == []
        assert energy == energy


def test_render_auto_uses_lj_for_iron(monkeypatch):
    monkeypatch.setenv("MEMORY_PROFILE", "render")
    calc, used, _errors = resolve_calculator("auto", species=["Fe"])
    atoms = bulk("Fe", "bcc", a=2.87)
    atoms.calc = calc
    assert used == "lj"
    assert atoms.get_potential_energy() == atoms.get_potential_energy()
    described = describe_calculator_workspace()
    assert described["render_calculators"] == ["emt", "lj", "morse"]
    assert described["calculators"]["lj"]["available"] is True
    with pytest.raises(ValueError, match="512 MB"):
        resolve_calculator("orb", species=["Cu"])
