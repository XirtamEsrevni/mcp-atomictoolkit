"""Optional Matbench Discovery calculator registry.

`matbench-discovery` is not imported unless a registry key is requested.
Listing uses a static first slice so capabilities do not pull in torch.
"""

from __future__ import annotations

import os
from typing import Any

# Small CPU-oriented first slice. The full registry is larger and not installed together.
DISCOVERY_MODELS = (
    "chgnet_0_3_0",
    "mace_mp_0",
    "sevennet_0",
    "mattersim_v1_5m",
    "orb_v2",
    "nequix_mp_1",
)


def discovery_blocked() -> bool:
    explicit = os.environ.get("MEMORY_PROFILE", "").strip().lower()
    if explicit in {"full", "off", "disabled"}:
        return False
    if explicit in {"render", "lite", "free", "low"}:
        return True
    return os.environ.get("RENDER", "").strip().lower() in {"1", "true", "yes", "on"} or bool(
        os.environ.get("RENDER_SERVICE_ID")
    )


def describe_discovery_models() -> dict[str, Any]:
    blocked = discovery_blocked()
    models = {}
    for key in DISCOVERY_MODELS:
        models[key] = {
            "available": False,
            "usable": False,
            "source": "matbench_discovery.calculators.load_calculator",
            "error": "blocked by Render memory profile" if blocked else "package not installed until requested",
        }
    return {
        "extra": "discovery",
        "loader": "matbench_discovery.calculators.load_calculator",
        "blocked_on_render": blocked,
        "models": models,
    }


def maybe_load_discovery(calculator_key: str):
    if calculator_key not in DISCOVERY_MODELS:
        return None
    if discovery_blocked():
        raise ValueError(
            f"Calculator '{calculator_key}' is a Matbench Discovery model and is blocked on Render."
        )
    calculator = _load_registry_calculator(calculator_key)
    return calculator, calculator_key, []


def _load_registry_calculator(calculator_key: str):
    """Load from load_calculator when present, otherwise CALCULATORS.

    Released matbench-discovery builds expose the registry as CALCULATORS and
    do not export load_calculator. Main-branch builds have both.
    """
    try:
        import matbench_discovery.calculators as registry
    except Exception as exc:
        raise RuntimeError(
            "matbench-discovery is not installed. Install the discovery extra before "
            f"using calculator_name={calculator_key!r}. Original error: {exc}"
        ) from exc

    loader = getattr(registry, "load_calculator", None)
    if callable(loader):
        return loader(calculator_key, device="cpu", dtype="float32")

    calculators = getattr(registry, "CALCULATORS", None)
    if calculators is None or calculator_key not in calculators:
        raise RuntimeError(
            f"matbench-discovery has no calculator factory for {calculator_key!r}. "
            "The installed build exposes neither load_calculator nor CALCULATORS[key]."
        )
    spec = calculators[calculator_key]
    if callable(spec):
        return spec()
    for name in ("make_calc", "load", "calculator"):
        factory = getattr(spec, name, None)
        if not callable(factory):
            continue
        try:
            return factory(device="cpu", dtype="float32")
        except TypeError:
            return factory()
    raise RuntimeError(
        f"CALCULATORS[{calculator_key!r}] has no callable calculator factory."
    )
