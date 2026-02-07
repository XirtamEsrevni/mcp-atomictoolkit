import sys
import types

import pytest

from mcp_atomictoolkit import calculators


def test_select_kim_model_id_uses_first_model(monkeypatch):
    def fake_get_available_models(species, potential_type):
        assert species == ["Al", "W"]
        assert potential_type == ["any"]
        return ["MODEL_1", "MODEL_2"]

    monkeypatch.setitem(
        sys.modules, "kim_query", types.SimpleNamespace(get_available_models=fake_get_available_models)
    )

    assert calculators._select_kim_model_id(["W", "Al"]) == "MODEL_1"


def test_select_kim_model_id_handles_dict_result(monkeypatch):
    def fake_get_available_models(species, potential_type):
        assert species == ["Al"]
        assert potential_type == ["any"]
        return [{"model_id": "KIM_ID"}]

    monkeypatch.setitem(
        sys.modules, "kim_query", types.SimpleNamespace(get_available_models=fake_get_available_models)
    )

    assert calculators._select_kim_model_id(["Al"]) == "KIM_ID"


def test_select_kim_model_id_warns_when_kim_query_missing(monkeypatch):
    monkeypatch.setitem(sys.modules, "kim_query", None)

    with pytest.warns(RuntimeWarning, match="kim-query is unavailable"):
        assert (
            calculators._select_kim_model_id(["Al"])
            == calculators.KIM_DEFAULT_MODEL
        )


def test_select_kim_model_id_defaults_when_no_models(monkeypatch):
    def fake_get_available_models(species, potential_type):
        assert species == ["Al"]
        assert potential_type == ["any"]
        return []

    monkeypatch.setitem(
        sys.modules, "kim_query", types.SimpleNamespace(get_available_models=fake_get_available_models)
    )

    assert (
        calculators._select_kim_model_id(["Al"]) == calculators.KIM_DEFAULT_MODEL
    )
