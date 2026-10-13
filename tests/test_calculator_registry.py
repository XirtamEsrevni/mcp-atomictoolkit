"""Tests for runtime calculator registration."""

from ase.build import bulk

from mcp_atomictoolkit.calculator_registry import (
    register_calculator,
    register_calculator_from_file,
    unregister_calculator,
)
from mcp_atomictoolkit.calculators import resolve_calculator


def test_register_and_resolve(tmp_path):
    source = tmp_path / "my_calc.py"
    source.write_text(
        "from ase.calculators.emt import EMT\n"
        "def get_calculator():\n"
        "    return EMT()\n",
        encoding="utf-8",
    )
    info = register_calculator_from_file("myemt", str(source))
    assert info["name"] == "myemt"

    atoms = bulk("Cu", "fcc", a=3.6)
    calc, used, errors = resolve_calculator("myemt", species=["Cu"])
    assert used == "myemt"
    assert errors == []
    atoms.calc = calc
    energy = atoms.get_potential_energy()
    assert energy == energy  # finite

    assert unregister_calculator("myemt") is True


def test_register_callable_directly():
    from ase.calculators.emt import EMT

    register_calculator("directemt", lambda: EMT())
    calc, used, _ = resolve_calculator("directemt", species=["Al"])
    assert used == "directemt"
    assert calc is not None
    unregister_calculator("directemt")
