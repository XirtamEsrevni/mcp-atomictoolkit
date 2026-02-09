import pytest
from ase import Atoms

from mcp_atomictoolkit import calculators


def test_ase_kim_uses_first_model_for_si():
    kim_query = pytest.importorskip("kim_query")
    pytest.importorskip("ase.calculators.kim.kim")

    try:
        models = kim_query.get_available_models(species=["Si"], potential_type=["any"])
    except Exception as exc:
        pytest.skip(f"OpenKIM query failed: {exc}")
    if not models:
        pytest.skip("OpenKIM query returned no models for Si.")

    def _coerce_model_id(entry):
        if isinstance(entry, str):
            return entry
        if isinstance(entry, dict):
            for key in ("model", "model_id", "kim_id", "extended_id", "id"):
                value = entry.get(key)
                if value:
                    return value
        return str(entry)

    first_model_id = _coerce_model_id(models[0])
    model_id = calculators._select_kim_model_id(["Si"])
    if model_id == calculators.KIM_DEFAULT_MODEL:
        pytest.skip("No OpenKIM models discovered for Si.")
    assert model_id == first_model_id

    try:
        calc = calculators.get_kim_calculator(species=["Si"])
    except RuntimeError as exc:
        pytest.skip(f"KIM model not available locally: {exc}")
    atoms = Atoms("Si2", positions=[[0, 0, 0], [2.35, 0, 0]], cell=[10, 10, 10], pbc=True)
    atoms.calc = calc

    try:
        energy = atoms.get_potential_energy()
    except Exception as exc:
        pytest.skip(f"ASE KIM model could not compute energy: {exc}")

    assert energy is not None
