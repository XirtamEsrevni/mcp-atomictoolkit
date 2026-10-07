import pytest

from mcp_atomictoolkit.discovery_calculators import describe_discovery_models
from mcp_atomictoolkit import calculators


def test_capabilities_list_discovery_models_without_import(monkeypatch):
    monkeypatch.setenv("MEMORY_PROFILE", "full")
    described = describe_discovery_models()
    assert "mace_mp_0" in described["models"]
    assert described["models"]["mace_mp_0"]["usable"] is False


def test_render_rejects_discovery_model_before_download(monkeypatch):
    monkeypatch.setenv("MEMORY_PROFILE", "render")
    with pytest.raises(ValueError, match="blocked on Render"):
        calculators.resolve_calculator("mace_mp_0")


def test_resolve_calls_load_calculator(monkeypatch):
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.setenv("MEMORY_PROFILE", "full")
    sentinel = object()
    calls = {}

    def _load(key):
        calls["key"] = key
        return sentinel, key, []

    monkeypatch.setattr(
        "mcp_atomictoolkit.discovery_calculators.maybe_load_discovery",
        _load,
    )
    calculator, used, errors = calculators.resolve_calculator("mace_mp_0")
    assert calls["key"] == "mace_mp_0"
    assert calculator is sentinel
    assert used == "mace_mp_0"
    assert errors == []
