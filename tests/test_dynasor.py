"""Tests for the optional Dynasor workflow."""

import pytest

from mcp_atomictoolkit.workflows import dynasor as dynasor_mod


def test_dynasor_blocked_on_render(monkeypatch):
    monkeypatch.setenv("MEMORY_PROFILE", "render")
    with pytest.raises(ValueError, match="Render"):
        dynasor_mod.submit_dynasor_job("traj.extxyz")


def test_dynasor_rejects_bad_params(monkeypatch):
    monkeypatch.setenv("MEMORY_PROFILE", "full")
    with pytest.raises(ValueError, match="dt_fs"):
        dynasor_mod.submit_dynasor_job("traj.extxyz", dt_fs=-1.0)
    with pytest.raises(ValueError, match="window_size"):
        dynasor_mod.submit_dynasor_job("traj.extxyz", window_size=1)
