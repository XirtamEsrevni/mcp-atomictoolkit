import importlib
import sys
import types


def test_configure_jax_for_cpu_overrides_environment(monkeypatch):
    monkeypatch.setenv("JAX_PLATFORMS", "cuda")
    monkeypatch.setenv("JAX_PLATFORM_NAME", "gpu")
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0")
    monkeypatch.setenv("JAX_CUDA_VISIBLE_DEVICES", "0")

    sys.modules.pop("mcp_atomictoolkit.calculators", None)
    calculators = importlib.import_module("mcp_atomictoolkit.calculators")

    assert calculators.os.environ["JAX_PLATFORMS"] == "cpu"
    assert calculators.os.environ["JAX_PLATFORM_NAME"] == "cpu"
    assert calculators.os.environ["CUDA_VISIBLE_DEVICES"] == ""
    assert calculators.os.environ["JAX_CUDA_VISIBLE_DEVICES"] == ""


def test_get_nequix_calculator_enforces_cpu_env(monkeypatch):
    monkeypatch.setenv("JAX_PLATFORMS", "cuda")
    monkeypatch.setenv("JAX_PLATFORM_NAME", "gpu")
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0")
    monkeypatch.setenv("JAX_CUDA_VISIBLE_DEVICES", "0")

    # Provide a lightweight fake nequix module so the test does not need the
    # heavyweight dependency to be installed.
    calculator_module = types.ModuleType("nequix.calculator")

    class DummyNequixCalculator:
        def __init__(self, model_name, backend):
            self.model_name = model_name
            self.backend = backend

    calculator_module.NequixCalculator = DummyNequixCalculator

    nequix_module = types.ModuleType("nequix")

    monkeypatch.setitem(sys.modules, "nequix", nequix_module)
    monkeypatch.setitem(sys.modules, "nequix.calculator", calculator_module)

    sys.modules.pop("mcp_atomictoolkit.calculators", None)
    calculators = importlib.import_module("mcp_atomictoolkit.calculators")

    calculator = calculators.get_nequix_calculator()

    assert isinstance(calculator, DummyNequixCalculator)
    assert calculator.backend == "jax"
    assert calculators.os.environ["JAX_PLATFORMS"] == "cpu"
    assert calculators.os.environ["JAX_PLATFORM_NAME"] == "cpu"
    assert calculators.os.environ["CUDA_VISIBLE_DEVICES"] == ""
    assert calculators.os.environ["JAX_CUDA_VISIBLE_DEVICES"] == ""
