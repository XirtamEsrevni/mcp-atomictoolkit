"""Tests for fixed-atom constraints."""

from pathlib import Path

from ase.build import bulk
from ase.io import read, write

from mcp_atomictoolkit.workflows.constraints import apply_fixed_atoms


def test_apply_fixed_atoms(tmp_path):
    atoms = bulk("Cu", "fcc", a=3.6, cubic=True)
    src = tmp_path / "in.cif"
    dst = tmp_path / "out.extxyz"
    write(src, atoms)
    result = apply_fixed_atoms(str(src), str(dst), indices=[0, 1])
    assert result["n_fixed"] == 2
    assert Path(dst).exists()
    loaded = read(dst)
    assert len(loaded.constraints) == 1


def test_fixed_atoms_rejects_bad_index(tmp_path):
    atoms = bulk("Cu", "fcc", a=3.6)
    src = tmp_path / "in.cif"
    write(src, atoms)
    import pytest
    with pytest.raises(ValueError, match="out of range"):
        apply_fixed_atoms(str(src), str(tmp_path / "out.cif"), indices=[99])
