"""Tests that small light jobs are allowed on Render."""

import pytest

from mcp_atomictoolkit.workflows import phonons, phonon_bands, neb


def test_phonon_dos_allows_small_light_on_render(monkeypatch):
    monkeypatch.setenv("MEMORY_PROFILE", "render")
    # Should not raise for emt + 1x1x1
    # We only check the guard; full job needs a file, so just call with a missing file
    # after the guard. Use a path that will fail later if the guard passes.
    try:
        phonons.submit_phonon_job("missing.cif", calculator_name="emt", supercell=[1, 1, 1])
    except ValueError as exc:
        assert "Render" not in str(exc)
    except Exception:
        pass  # file missing or other is fine


def test_phonon_dos_blocks_large_on_render(monkeypatch):
    monkeypatch.setenv("MEMORY_PROFILE", "render")
    with pytest.raises(ValueError, match="Render"):
        phonons.submit_phonon_job("x.cif", calculator_name="emt", supercell=[2, 2, 2])


def test_neb_allows_small_light_on_render(monkeypatch):
    monkeypatch.setenv("MEMORY_PROFILE", "render")
    try:
        neb.submit_neb_job("a.cif", "b.cif", n_images=3, calculator_name="emt")
    except ValueError as exc:
        assert "Render" not in str(exc)
    except Exception:
        pass


def test_neb_blocks_many_images_on_render(monkeypatch):
    monkeypatch.setenv("MEMORY_PROFILE", "render")
    with pytest.raises(ValueError, match="Render"):
        neb.submit_neb_job("a.cif", "b.cif", n_images=5, calculator_name="emt")
