"""Calculator configuration helpers for MLIP backends."""

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nequix.calculator import NequixCalculator
    from orb_models.forcefield.calculator import ORBCalculator

NEQUIX_DEFAULT_MODEL = "nequix-mp-1"
NEQUIX_DEFAULT_BACKEND = "jax"


def _configure_jax_for_cpu() -> None:
    """Force JAX/Nequix execution on CPU-only runtimes."""
    # We intentionally overwrite these values to guarantee CPU execution even
    # when a hosting environment pre-sets GPU defaults.
    os.environ["JAX_PLATFORMS"] = "cpu"
    os.environ["JAX_PLATFORM_NAME"] = "cpu"
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ["JAX_CUDA_VISIBLE_DEVICES"] = ""


# Configure CPU-only defaults as soon as this module is imported so that any
# later JAX imports (triggered inside Nequix) inherit the safe environment.
_configure_jax_for_cpu()


def _normalize_calculator_name(calculator_name: str) -> str:
    """Return canonical calculator key, accepting common aliases/typos."""
    aliases = {
        "neqix": "nequix",
    }
    return aliases.get(calculator_name.lower(), calculator_name.lower())


def get_orb_calculator() -> "ORBCalculator":
    """Initialize Orb calculator."""
    from orb_models.forcefield import pretrained
    from orb_models.forcefield.calculator import ORBCalculator

    orbff = pretrained.orb_v2(device="cpu")
    calculator = ORBCalculator(orbff, device="cpu")
    return calculator


def get_nequix_calculator(
    model_name: str = NEQUIX_DEFAULT_MODEL,
    backend: str = NEQUIX_DEFAULT_BACKEND,
) -> "NequixCalculator":
    """Initialize Nequix calculator on CPU."""
    if backend == "jax":
        _configure_jax_for_cpu()

    from nequix.calculator import NequixCalculator

    return NequixCalculator(
        model_name,
        backend=backend,
    )


def get_calculator(calculator_name: str) -> "ORBCalculator | NequixCalculator":
    """Return an ASE calculator for the requested MLIP."""
    calculator_key = _normalize_calculator_name(calculator_name)
    if calculator_key == "orb":
        return get_orb_calculator()
    if calculator_key == "nequix":
        return get_nequix_calculator()
    raise ValueError(f"Unknown MLIP type: {calculator_name}")
