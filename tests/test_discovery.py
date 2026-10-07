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


def test_released_registry_uses_calculators_mapping(monkeypatch):
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.setenv("MEMORY_PROFILE", "full")
    sentinel = object()

    class _Registry:
        CALCULATORS = {"mace_mp_0": lambda: sentinel}

    import sys, types
    module = types.ModuleType("matbench_discovery.calculators")
    module.CALCULATORS = _Registry.CALCULATORS
    monkeypatch.setitem(sys.modules, "matbench_discovery", types.ModuleType("matbench_discovery"))
    monkeypatch.setitem(sys.modules, "matbench_discovery.calculators", module)
    from mcp_atomictoolkit.discovery_calculators import maybe_load_discovery
    calculator, used, errors = maybe_load_discovery("mace_mp_0")
    assert calculator is sentinel
    assert used == "mace_mp_0"
    assert errors == []


def test_all_registry_keys_are_listed():
    from mcp_atomictoolkit.discovery_calculators import DISCOVERY_MODELS
    described = describe_discovery_models()
    assert len(DISCOVERY_MODELS) == 53
    assert "emt" not in DISCOVERY_MODELS
    assert set(described["models"]) == set(DISCOVERY_MODELS)
    assert "grace_2l_oam" in described["models"]
    assert "equflashv2_45m_oam" in described["models"]
