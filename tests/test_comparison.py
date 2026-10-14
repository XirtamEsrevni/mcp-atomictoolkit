"""Tests for structure RMSD."""

from pathlib import Path

import numpy as np
from ase.build import bulk
from ase.io import write

from mcp_atomictoolkit.analysis.comparison import structure_rmsd


def test_rmsd_identical(tmp_path):
    atoms = bulk("Cu", "fcc", a=3.6)
    path = tmp_path / "a.cif"
    write(path, atoms)
    result = structure_rmsd(str(path), str(path))
    assert result["rmsd_Angstrom"] < 1e-6
    assert result["n_atoms"] == 1


def test_rmsd_displaced(tmp_path):
    ref = bulk("Cu", "fcc", a=3.6, cubic=True)
    tgt = ref.copy()
    # Displace only one atom so alignment cannot fully cancel it
    tgt.positions[0] += np.array([0.15, 0.0, 0.0])
    ref_path = tmp_path / "ref.cif"
    tgt_path = tmp_path / "tgt.cif"
    write(ref_path, ref)
    write(tgt_path, tgt)
    result = structure_rmsd(str(ref_path), str(tgt_path), align=True)
    assert result["rmsd_Angstrom"] > 0.01
    assert result["rmsd_Angstrom"] < 0.3
    assert result["aligned"] is True


def test_rmsd_atom_count_mismatch(tmp_path):
    a = bulk("Cu", "fcc", a=3.6)
    b = bulk("Cu", "fcc", a=3.6) * (2, 1, 1)
    pa = tmp_path / "a.cif"
    pb = tmp_path / "b.cif"
    write(pa, a)
    write(pb, b)
    import pytest
    with pytest.raises(ValueError, match="Atom count"):
        structure_rmsd(str(pa), str(pb))
