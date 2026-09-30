"""Host memory profiles so a 512 MB Render dyno refuses jobs that would OOM."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, Mapping, MutableMapping, Optional


def _truthy(value: Optional[str]) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on", "render"}


def detect_profile_name() -> str:
    """Return render | full.

    Render injects RENDER=true on every service. MEMORY_PROFILE overrides that.
    """
    explicit = os.environ.get("MEMORY_PROFILE", "").strip().lower()
    if explicit in {"render", "lite", "free", "low"}:
        return "render"
    if explicit in {"full", "off", "disabled"}:
        return "full"
    if _truthy(os.environ.get("RENDER")) or os.environ.get("RENDER_SERVICE_ID"):
        return "render"
    if _truthy(os.environ.get("MCP_LOW_MEMORY")):
        return "render"
    return "full"


@dataclass(frozen=True)
class MemoryProfile:
    name: str
    max_atoms: int
    max_md_steps: int
    max_optimize_steps: int
    max_eos_points: int
    max_rdf_bins: int
    max_supercell_atoms: int
    allowed_calculators: tuple[str, ...]
    blocked_tools: tuple[str, ...]
    blocked_structure_types: tuple[str, ...]
    note: str

    def public_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["allowed_calculators"] = list(self.allowed_calculators)
        payload["blocked_tools"] = list(self.blocked_tools)
        payload["blocked_structure_types"] = list(self.blocked_structure_types)
        return payload


FULL_PROFILE = MemoryProfile(
    name="full",
    max_atoms=10_000,
    max_md_steps=1_000_000,
    max_optimize_steps=10_000,
    max_eos_points=21,
    max_rdf_bins=2000,
    max_supercell_atoms=10_000,
    allowed_calculators=("auto", "kim", "orb", "nequix", "emt"),
    blocked_tools=(),
    blocked_structure_types=(),
    note="No host memory cap.",
)

RENDER_PROFILE = MemoryProfile(
    name="render",
    max_atoms=32,
    max_md_steps=40,
    max_optimize_steps=25,
    max_eos_points=4,
    max_rdf_bins=80,
    max_supercell_atoms=32,
    allowed_calculators=("auto", "emt"),
    blocked_tools=(
        "analyze_trajectory_workflow",
        "autocorrelation_workflow",
    ),
    blocked_structure_types=(
        "amorphous",
        "liquid",
        "polycrystal",
        "bicrystal",
    ),
    note=(
        "Render free tier is ~512 MB. EMT metals only, small cells, short MD. "
        "Trajectory analysis is disabled so the dyno is not killed."
    ),
)


def current_profile() -> MemoryProfile:
    return RENDER_PROFILE if detect_profile_name() == "render" else FULL_PROFILE


def allowed_calculators() -> tuple[str, ...]:
    return current_profile().allowed_calculators


def constrain_calculator_name(calculator_name: str) -> str:
    profile = current_profile()
    if profile.name != "render":
        return calculator_name
    requested = (calculator_name or "auto").strip().lower()
    if requested in {"", "auto", "emt", "ase-emt", "ase_emt"}:
        return "emt" if requested.startswith("emt") or requested.startswith("ase") else "auto"
    raise ValueError(
        f"calculator_name={calculator_name!r} is not allowed on the Render memory profile. "
        "Use 'emt' or 'auto' (EMT only). Orb/Nequix/KIM will OOM a 512 MB dyno."
    )


def _repeat_product(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int):
        return max(value, 1)
    if isinstance(value, (list, tuple)) and value:
        product = 1
        for item in value:
            product *= max(int(item), 1)
        return product
    return None


def constrain_tool_call(tool_name: str, kwargs: Mapping[str, Any]) -> Dict[str, Any]:
    """Clamp or reject a tool invocation for the active host profile."""
    profile = current_profile()
    updated: Dict[str, Any] = dict(kwargs)
    if profile.name != "render":
        return updated

    if tool_name in profile.blocked_tools:
        raise ValueError(
            f"{tool_name} is disabled on Render ({profile.note})"
        )

    structure_type = str(updated.get("structure_type") or "").lower()
    if structure_type in profile.blocked_structure_types:
        raise ValueError(
            f"structure_type={structure_type!r} is disabled on Render. "
            "Build a small bulk/surface/molecule instead."
        )

    if "calculator_name" in updated:
        updated["calculator_name"] = constrain_calculator_name(
            str(updated.get("calculator_name") or "auto")
        )

    if "steps" in updated and updated["steps"] is not None:
        updated["steps"] = min(int(updated["steps"]), profile.max_md_steps)
    if "max_steps" in updated and updated["max_steps"] is not None:
        updated["max_steps"] = min(int(updated["max_steps"]), profile.max_optimize_steps)
    if "n_points" in updated and updated["n_points"] is not None:
        updated["n_points"] = min(int(updated["n_points"]), profile.max_eos_points)
    if "rdf_bins" in updated and updated["rdf_bins"] is not None:
        updated["rdf_bins"] = min(int(updated["rdf_bins"]), profile.max_rdf_bins)

    operation = str(updated.get("operation") or "").lower()
    op_kwargs = dict(updated.get("operation_kwargs") or {})
    if operation == "supercell":
        repeats = op_kwargs.get("repeat") or op_kwargs.get("repeats") or op_kwargs.get("size")
        product = _repeat_product(repeats)
        if product is not None and product > 8:
            raise ValueError(
                f"supercell repeat {repeats!r} is too large for Render "
                f"(product={product}, max 8)."
            )

    builder = dict(updated.get("builder_kwargs") or {})
    size = builder.get("size") or builder.get("repeat")
    product = _repeat_product(size)
    if product is not None and product > 8:
        raise ValueError(
            f"builder size {size!r} is too large for Render (product={product}, max 8)."
        )

    if "symbols" in updated and isinstance(updated["symbols"], Iterable):
        n_atoms = len(list(updated["symbols"]))
        if n_atoms > profile.max_atoms:
            raise ValueError(
                f"{n_atoms} atoms exceeds the Render cap of {profile.max_atoms}."
            )
    return updated


def apply_limits_to_kwargs(kwargs: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    constrained = constrain_tool_call("unknown", kwargs)
    kwargs.clear()
    kwargs.update(constrained)
    return kwargs
