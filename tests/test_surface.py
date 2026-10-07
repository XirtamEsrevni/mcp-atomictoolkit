import os

import pytest

from mcp_atomictoolkit.calculators import describe_calculator_workspace
from mcp_atomictoolkit.workflows.surface import surface_energy_workflow


def test_surface_energy_emt_copper():
    result = surface_energy_workflow(
        formula="Cu",
        crystal_system="fcc",
        lattice_constant=3.6,
        miller=[1, 1, 1],
        size=[1, 1, 1],
        layers=3,
        vacuum=6.0,
        calculator_name="emt",
    )
    assert result["calculator_used"] == "emt"
    assert result["n_slab_atoms"] == 3
    assert result["area_A2"] > 0
    assert result["surface_energy_J_m2"] > 0


def test_render_rejects_large_slab(monkeypatch):
    monkeypatch.setenv("MEMORY_PROFILE", "render")
    with pytest.raises(ValueError, match="32 atoms"):
        surface_energy_workflow(size=[4, 4, 1], layers=6, calculator_name="emt")


def test_render_does_not_mark_kim_available(monkeypatch):
    monkeypatch.setenv("MEMORY_PROFILE", "render")
    described = describe_calculator_workspace()
    assert described["calculators"]["kim"]["available"] is False
    assert described["calculators"]["emt"]["available"] is True
    assert "Render" in described["calculators"]["kim"]["error"]
