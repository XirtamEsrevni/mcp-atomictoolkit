import os

from mcp_atomictoolkit.deploy_profile import (
    constrain_calculator_name,
    constrain_tool_call,
    detect_profile_name,
)


def test_render_env_selects_profile(monkeypatch):
    monkeypatch.delenv("MEMORY_PROFILE", raising=False)
    monkeypatch.setenv("RENDER", "true")
    assert detect_profile_name() == "render"


def test_explicit_full_overrides_render(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("MEMORY_PROFILE", "full")
    assert detect_profile_name() == "full"


def test_render_blocks_mlip_and_heavy_tools(monkeypatch):
    monkeypatch.setenv("MEMORY_PROFILE", "render")
    assert constrain_calculator_name("auto") == "auto"
    try:
        constrain_calculator_name("orb")
        raise AssertionError("orb should be rejected")
    except ValueError as exc:
        assert "not allowed" in str(exc)

    clamped = constrain_tool_call(
        "run_md_workflow",
        {"steps": 5000, "max_steps": 400, "calculator_name": "auto"},
    )
    assert clamped["steps"] == 40
    assert clamped["max_steps"] == 25

    try:
        constrain_tool_call("autocorrelation_workflow", {})
        raise AssertionError("autocorrelation should be blocked")
    except ValueError as exc:
        assert "disabled on Render" in str(exc)

    try:
        constrain_tool_call(
            "build_structure_workflow",
            {"structure_type": "polycrystal"},
        )
        raise AssertionError("polycrystal should be blocked")
    except ValueError as exc:
        assert "polycrystal" in str(exc)


def test_full_profile_is_a_no_op(monkeypatch):
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.delenv("RENDER_SERVICE_ID", raising=False)
    monkeypatch.setenv("MEMORY_PROFILE", "full")
    out = constrain_tool_call("run_md_workflow", {"steps": 5000, "calculator_name": "orb"})
    assert out["steps"] == 5000
    assert out["calculator_name"] == "orb"
