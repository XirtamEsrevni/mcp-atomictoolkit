import sys
import types

import pytest

from mcp_atomictoolkit import calculators


def _install_orb_stub(monkeypatch):
    forcefield = types.ModuleType("orb_models.forcefield")
    calculator_mod = types.ModuleType("orb_models.forcefield.calculator")

    def orb_v2(device="cpu"):
        return {"device": device}

    class ORBCalculator:
        def __init__(self, orbff, device="cpu"):
            self.orbff = orbff
            self.device = device

    forcefield.pretrained = types.SimpleNamespace(orb_v2=orb_v2)
    calculator_mod.ORBCalculator = ORBCalculator

    monkeypatch.setitem(sys.modules, "orb_models.forcefield", forcefield)
    monkeypatch.setitem(sys.modules, "orb_models.forcefield.calculator", calculator_mod)


def _install_nequix_stub(monkeypatch):
    nequix_calculator = types.ModuleType("nequix.calculator")

    class NequixCalculator:
        def __init__(self, model_name, backend="jax"):
            self.model_name = model_name
            self.backend = backend

    nequix_calculator.NequixCalculator = NequixCalculator
    monkeypatch.setitem(sys.modules, "nequix.calculator", nequix_calculator)


def _install_kim_stub(monkeypatch):
    kim_module = types.ModuleType("ase.calculators.kim.kim")

    class KIM:
        def __init__(self, model_id):
            self.model_id = model_id

    kim_module.KIM = KIM
    monkeypatch.setitem(sys.modules, "ase.calculators.kim.kim", kim_module)


def test_normalize_calculator_name_aliases():
    assert calculators._normalize_calculator_name("neqix") == "nequix"
    assert calculators._normalize_calculator_name("openkim") == "kim"
    assert calculators._normalize_calculator_name("kim-model") == "kim"
    assert calculators._normalize_calculator_name("orb") == "orb"


def test_normalize_species_sorted_unique():
    assert calculators._normalize_species(["W", "Al", "W"]) == ["Al", "W"]
    assert calculators._normalize_species(None) == []


def test_get_calculator_orb(monkeypatch):
    _install_orb_stub(monkeypatch)
    calculator = calculators.get_calculator("orb")
    assert calculator.device == "cpu"
    assert calculator.orbff["device"] == "cpu"


def test_get_calculator_nequix(monkeypatch):
    _install_nequix_stub(monkeypatch)
    calculator = calculators.get_calculator("nequix")
    assert calculator.model_name == calculators.NEQUIX_DEFAULT_MODEL


def test_get_calculator_kim(monkeypatch):
    _install_kim_stub(monkeypatch)
    kim_query = types.ModuleType("kim_query")
    kim_query.get_available_models = lambda species, potential_type: ["TEST_MODEL"]
    monkeypatch.setitem(sys.modules, "kim_query", kim_query)

    calculator = calculators.get_calculator("kim", species=["Al"])
    assert calculator.model_id == "TEST_MODEL"


def test_get_kim_calculator_import_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "ase.calculators.kim.kim", None)
    monkeypatch.setitem(sys.modules, "kim_query", None)
    with pytest.raises(RuntimeError, match="Failed to import ASE KIM calculator"):
        calculators.get_kim_calculator(species=["Al"])


def test_resolve_calculator_falls_back_when_requested_fails(monkeypatch):
    def fake_get_calculator_by_key(key, species):
        if key == "kim":
            raise RuntimeError("kim missing")
        return {"name": key}

    monkeypatch.setattr(calculators, "_get_calculator_by_key", fake_get_calculator_by_key)

    calculator, used, errors = calculators.resolve_calculator("kim", species=["Al"])
    assert calculator == {"name": "orb"}
    assert used == "orb"
    assert any(error.startswith("kim:") for error in errors)
