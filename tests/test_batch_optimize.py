"""Tests for batch geometry optimization."""

from pathlib import Path

from ase.build import bulk
from ase.io import write

from mcp_atomictoolkit.workflows.batch_optimize import batch_optimize


def test_batch_optimize_emt(tmp_path):
    paths = []
    for a in (3.7, 3.8):
        atoms = bulk("Cu", "fcc", a=a)
        p = tmp_path / f"cu_{a}.cif"
        write(p, atoms)
        paths.append(str(p))

    out = tmp_path / "relaxed"
    result = batch_optimize(
        paths,
        str(out),
        calculator_name="emt",
        max_steps=5,
        fmax=0.5,
    )
    assert result["n_structures"] == 2
    assert (out / "relaxed_000.extxyz").exists()
    assert all(r["calculator_used"] == "emt" for r in result["results"])


def test_batch_optimize_rejects_too_many(tmp_path):
    atoms = bulk("Cu", "fcc", a=3.6)
    p = tmp_path / "a.cif"
    write(p, atoms)
    import pytest
    with pytest.raises(ValueError, match="limited"):
        batch_optimize([str(p)] * 15, str(tmp_path / "o"), max_structures=10)
