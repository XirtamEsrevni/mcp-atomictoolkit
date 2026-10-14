"""Tests for substitutional defect."""

from pathlib import Path

from ase.build import bulk
from ase.io import read, write

from mcp_atomictoolkit.workflows.substitute import substitute_atom


def test_substitute_cu_to_ni(tmp_path):
    atoms = bulk("Cu", "fcc", a=3.6, cubic=True)
    src = tmp_path / "cu.cif"
    dst = tmp_path / "cuni.cif"
    write(src, atoms)
    result = substitute_atom(str(src), str(dst), index=0, new_symbol="Ni")
    assert result["old_symbol"] == "Cu"
    assert result["new_symbol"] == "Ni"
    loaded = read(dst)
    assert loaded[0].symbol == "Ni"
    assert loaded.get_chemical_formula() == "Cu3Ni"


def test_substitute_rejects_bad_index(tmp_path):
    atoms = bulk("Cu", "fcc", a=3.6)
    src = tmp_path / "a.cif"
    write(src, atoms)
    import pytest
    with pytest.raises(ValueError, match="out of range"):
        substitute_atom(str(src), str(tmp_path / "b.cif"), index=99, new_symbol="Ni")
