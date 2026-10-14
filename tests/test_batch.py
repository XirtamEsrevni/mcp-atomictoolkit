"""Tests for batch single-point."""

from pathlib import Path

from ase.build import bulk
from ase.io import write

from mcp_atomictoolkit.workflows.batch import batch_single_point


def test_batch_single_point_emt(tmp_path):
    paths = []
    for a in (3.5, 3.6, 3.7):
        atoms = bulk("Cu", "fcc", a=a)
        p = tmp_path / f"cu_{a}.cif"
        write(p, atoms)
        paths.append(str(p))

    result = batch_single_point(paths, calculator_name="emt")
    assert result["n_structures"] == 3
    assert len(result["results"]) == 3
    assert result["energy_min_eV"] <= result["energy_mean_eV"] <= result["energy_max_eV"]
    assert all(r["calculator_used"] == "emt" for r in result["results"])


def test_batch_rejects_too_many(tmp_path):
    atoms = bulk("Cu", "fcc", a=3.6)
    p = tmp_path / "a.cif"
    write(p, atoms)
    import pytest
    with pytest.raises(ValueError, match="limited"):
        batch_single_point([str(p)] * 25, calculator_name="emt", max_structures=20)
