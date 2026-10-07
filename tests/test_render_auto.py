import pytest

from mcp_atomictoolkit import calculators


def test_render_auto_is_emt_only(monkeypatch):
    monkeypatch.setenv("MEMORY_PROFILE", "render")
    described = calculators.describe_calculator_workspace()
    assert described["auto_order"] == ["emt"]
    assert described["host"]["disk"] == "ephemeral"

    def _get(key, species=None):
        if key == "emt":
            return "emt-calc"
        raise RuntimeError(key)

    monkeypatch.setattr(calculators, "_get_calculator_by_key", _get)
    calculator, used, _errors = calculators.resolve_calculator("auto")
    assert used == "emt"
    assert calculator == "emt-calc"
    with pytest.raises(RuntimeError, match="kim"):
        calculators.resolve_calculator("kim")
