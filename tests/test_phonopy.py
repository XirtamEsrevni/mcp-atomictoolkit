"""Tests for the optional phonopy job."""

import pytest

from mcp_atomictoolkit.workflows import phonopy_job as pj


def test_phonopy_blocked_on_render(monkeypatch):
    monkeypatch.setenv("MEMORY_PROFILE", "render")
    with pytest.raises(ValueError, match="Render"):
        pj.submit_phonopy_job("cu.cif")


def test_phonopy_requires_package(monkeypatch):
    monkeypatch.setenv("MEMORY_PROFILE", "full")
    import builtins
    real = builtins.__import__

    def fake(name, *a, **k):
        if name == "phonopy" or name.startswith("phonopy."):
            raise ImportError("no phonopy")
        return real(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake)
    with pytest.raises(RuntimeError, match="phonopy is not installed"):
        pj.submit_phonopy_job("cu.cif")
