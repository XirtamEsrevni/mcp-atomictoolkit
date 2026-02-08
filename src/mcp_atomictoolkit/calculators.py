"""Calculator configuration helpers for MLIP backends."""

import logging
import os
import warnings
from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from nequix.calculator import NequixCalculator
    from orb_models.forcefield.calculator import ORBCalculator
    from ase.calculators.kim.kim import KIM as KIMCalculator

NEQUIX_DEFAULT_MODEL = "nequix-mp-1"
NEQUIX_DEFAULT_BACKEND = "jax"
KIM_DEFAULT_MODEL = "LJ_ElliottAkerson_2015_Universal__MO_959249795837_003"
# Default to auto-selection so low-resource environments can fall back when
# heavyweight dependencies (e.g., KIM API) are unavailable.
DEFAULT_CALCULATOR_NAME = "auto"

logger = logging.getLogger("mcp_atomictoolkit.calculators")


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
    normalized = calculator_name.strip().lower()
    aliases = {
        "auto-select": "auto",
        "auto_select": "auto",
        "neqix": "nequix",
        "orb of nequix": "orb",
        "orb-of-nequix": "orb",
        "openkim": "kim",
        "kim-model": "kim",
        "kim_model": "kim",
    }
    return aliases.get(normalized, normalized)


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


def _normalize_species(species: Sequence[str] | None) -> list[str]:
    """Return a sorted, unique list of chemical symbols."""
    if not species:
        return []
    unique_species = {symbol for symbol in species if symbol}
    return sorted(unique_species)


def _select_kim_model_id(
    species: Sequence[str] | None,
) -> str:
    """Select the first available KIM model ID for the given species."""
    normalized_species = _normalize_species(species)
    try:
        from kim_query import get_available_models
    except Exception as exc:
        warnings.warn(
            (
                "kim-query is unavailable; falling back to the default KIM model "
                f"'{KIM_DEFAULT_MODEL}'. Original error: {exc}"
            ),
            RuntimeWarning,
        )
        return KIM_DEFAULT_MODEL

    if not normalized_species:
        return KIM_DEFAULT_MODEL

    try:
        models = get_available_models(
            species=normalized_species,
            potential_type=["any"],
        )
    except Exception as exc:
        warnings.warn(
            (
                "Failed to query OpenKIM models; falling back to the default KIM model "
                f"'{KIM_DEFAULT_MODEL}'. Original error: {exc}"
            ),
            RuntimeWarning,
        )
        return KIM_DEFAULT_MODEL

    if not models:
        return KIM_DEFAULT_MODEL

    first = models[0]
    if isinstance(first, str):
        return first
    if isinstance(first, dict):
        for key in ("model", "model_id", "kim_id", "extended_id", "id"):
            value = first.get(key)
            if value:
                return value
        return KIM_DEFAULT_MODEL
    return str(first)


def get_kim_calculator(
    species: Sequence[str] | None = None,
) -> "KIMCalculator":
    """Initialize a KIM calculator for the requested species."""
    model_id = _select_kim_model_id(species)
    try:
        from ase.calculators.kim.kim import KIM
    except Exception as exc:
        message = (
            "Failed to import ASE KIM calculator. Ensure the KIM API and kimpy are "
            "installed. See https://openkim.org/kim-api for installation instructions."
        )
        raise RuntimeError(message) from exc
    try:
        return KIM(model_id)
    except Exception as exc:
        message = (
            f"Failed to initialize KIM model '{model_id}'. Ensure the KIM API and kimpy "
            "are installed and that the model is available locally."
        )
        raise RuntimeError(message) from exc


def _get_calculator_by_key(
    calculator_key: str,
    species: Sequence[str] | None,
) -> "ORBCalculator | NequixCalculator | KIMCalculator":
    if calculator_key == "orb":
        return get_orb_calculator()
    if calculator_key == "nequix":
        return get_nequix_calculator()
    if calculator_key == "kim":
        return get_kim_calculator(species=species)
    raise ValueError(f"Unknown MLIP type: {calculator_key}")


def resolve_calculator(
    calculator_name: str,
    species: Sequence[str] | None = None,
) -> tuple["ORBCalculator | NequixCalculator | KIMCalculator", str, list[str]]:
    """Resolve a calculator, optionally falling back when auto-selection is used."""
    calculator_key = _normalize_calculator_name(calculator_name)
    available_candidates = ("kim", "orb", "nequix")
    if calculator_key == "auto":
        candidates = available_candidates
    else:
        candidates = (calculator_key,)

    errors: list[str] = []
    attempted: list[str] = []
    for candidate in candidates:
        attempted.append(candidate)
        try:
            calculator = _get_calculator_by_key(candidate, species)
        except Exception as exc:
            errors.append(f"{candidate}: {exc}")
            logger.warning(
                "Calculator '%s' unavailable: %s",
                candidate,
                exc,
                exc_info=True,
            )
            continue
        return calculator, candidate, errors

    if calculator_key != "auto":
        fallback_candidates = [c for c in available_candidates if c != calculator_key]
        for candidate in fallback_candidates:
            attempted.append(candidate)
            try:
                calculator = _get_calculator_by_key(candidate, species)
            except Exception as exc:
                errors.append(f"{candidate}: {exc}")
                logger.warning(
                    "Calculator '%s' unavailable: %s",
                    candidate,
                    exc,
                    exc_info=True,
                )
                continue
            return calculator, candidate, errors

    attempted_summary = ", ".join(attempted)
    detail = "; ".join(errors) or "no additional error details"
    raise RuntimeError(
        f"Failed to initialize any MLIP calculator (attempted: {attempted_summary}). Details: {detail}"
    )


def get_calculator(
    calculator_name: str,
    species: Sequence[str] | None = None,
) -> "ORBCalculator | NequixCalculator | KIMCalculator":
    """Return an ASE calculator for the requested MLIP."""
    calculator, _used, _errors = resolve_calculator(
        calculator_name,
        species=species,
    )
    return calculator
