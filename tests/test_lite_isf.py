"""Tests for the lightweight intermediate scattering function."""

from pathlib import Path

import numpy as np
from ase.build import bulk
from ase.io import write

from mcp_atomictoolkit.analysis.lite_isf import lite_intermediate_scattering


def test_lite_isf_identical_frames(tmp_path):
    atoms = bulk("Cu", "fcc", a=3.6, cubic=True)
    frames = [atoms.copy() for _ in range(10)]
    path = tmp_path / "static.extxyz"
    write(path, frames)
    result = lite_intermediate_scattering(str(path), q_magnitude=2.0, dt_fs=1.0, max_lag=5)
    # Identical frames → F(q,t) ≈ 1 for all lags
    assert result["n_frames"] == 10
    assert all(abs(v - 1.0) < 1e-6 for v in result["F_qt"])


def test_lite_isf_rejects_bad_params(tmp_path):
    atoms = bulk("Cu", "fcc", a=3.6)
    path = tmp_path / "a.cif"
    write(path, atoms)
    import pytest
    with pytest.raises(ValueError, match="q_magnitude"):
        lite_intermediate_scattering(str(path), q_magnitude=-1.0)
