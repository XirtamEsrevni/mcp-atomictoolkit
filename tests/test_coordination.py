"""Tests for coordination analysis."""

from pathlib import Path

from ase.build import bulk
from ase.io import write

from mcp_atomictoolkit.analysis.coordination import coordination_analysis


def test_coordination_fcc_copper(tmp_path):
    atoms = bulk("Cu", "fcc", a=3.6, cubic=True)
    path = tmp_path / "cu.cif"
    write(path, atoms)
    result = coordination_analysis(str(path), cutoff=3.0)
    assert result["n_atoms"] == 4
    # FCC nearest neighbors within ~2.55 Å; 3.0 Å should catch them
    assert result["mean_coordination"] >= 6
    assert "Cu" in result["species_average_coordination"]


def test_coordination_rejects_bad_cutoff(tmp_path):
    atoms = bulk("Cu", "fcc", a=3.6)
    path = tmp_path / "a.cif"
    write(path, atoms)
    import pytest
    with pytest.raises(ValueError, match="cutoff"):
        coordination_analysis(str(path), cutoff=-1.0)
