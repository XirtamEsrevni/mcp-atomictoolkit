"""Tests for the elastic tensor workflow."""

from pathlib import Path

import pytest
from ase.build import bulk
from ase.io import write

from mcp_atomictoolkit.workflows.elastic import compute_elastic_tensor


def test_elastic_tensor_emt_copper(tmp_path):
    atoms = bulk("Cu", "fcc", a=3.6)
    path = tmp_path / "cu.cif"
    write(path, atoms)
    result = compute_elastic_tensor(str(path), calculator_name="emt", strain=0.005)
    assert result["calculator_used"] == "emt"
    cij = result["cij_GPa"]
    assert len(cij) == 6
    assert len(cij[0]) == 6
    # Bulk modulus should be positive for EMT Cu
    assert result["bulk_modulus_GPa"] > 0
    # Diagonal components should be the same order of magnitude for cubic EMT Cu
    assert cij[0][0] > 50
    assert cij[1][1] > 50
    assert cij[2][2] > 50


def test_elastic_rejects_bad_strain(tmp_path):
    atoms = bulk("Cu", "fcc", a=3.6)
    path = tmp_path / "cu.cif"
    write(path, atoms)
    with pytest.raises(ValueError, match="strain"):
        compute_elastic_tensor(str(path), calculator_name="emt", strain=0.1)
