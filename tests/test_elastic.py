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
    # Symmetry: C11 ~ C22 ~ C33 for cubic
    assert abs(cij[0][0] - cij[1][1]) < 5.0
    assert abs(cij[1][1] - cij[2][2]) < 5.0


def test_elastic_rejects_bad_strain(tmp_path):
    atoms = bulk("Cu", "fcc", a=3.6)
    path = tmp_path / "cu.cif"
    write(path, atoms)
    with pytest.raises(ValueError, match="strain"):
        compute_elastic_tensor(str(path), calculator_name="emt", strain=0.1)
