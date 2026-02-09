import logging
import os
import platform
import resource
import traceback
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Dict, List, Optional
from fastmcp import FastMCP

from mcp_atomictoolkit.artifact_store import with_downloadable_artifacts
from mcp_atomictoolkit.calculators import DEFAULT_CALCULATOR_NAME
from mcp_atomictoolkit.workflows.core import (
    analyze_structure_workflow as analyze_structure_workflow_impl,
    analyze_trajectory_workflow as analyze_trajectory_workflow_impl,
    autocorrelation_workflow as autocorrelation_workflow_impl,
    build_structure_workflow as build_structure_workflow_impl,
    optimize_structure_workflow as optimize_structure_workflow_impl,
    run_md_workflow as run_md_workflow_impl,
    single_point_workflow as single_point_workflow_impl,
    write_structure_workflow as write_structure_workflow_impl,
)

mcp = FastMCP(
    "atomictoolkit",
)

logger = logging.getLogger("mcp_atomictoolkit.tools")


def _compact_kwargs(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Compact large args in logs while preserving useful context."""
    compacted: Dict[str, Any] = {}
    for key, value in kwargs.items():
        if isinstance(value, str) and len(value) > 200:
            compacted[key] = f"<str:{len(value)} chars>"
        elif isinstance(value, list) and len(value) > 25:
            compacted[key] = f"<list:{len(value)} items>"
        elif isinstance(value, dict) and len(value) > 25:
            compacted[key] = f"<dict:{len(value)} keys>"
        else:
            compacted[key] = value
    return compacted


def _error_hints(tool_name: str, kwargs: Dict[str, Any], exc: Exception) -> List[str]:
    hints: List[str] = []
    msg = str(exc).lower()
    crystal_system = str(kwargs.get("crystal_system", "")).lower()
    oom_signals = ("out of memory", "oom", "killed process", "cuda out of memory")

    if tool_name == "build_structure_workflow" and crystal_system == "hcp":
        if "cubic" in msg or kwargs.get("builder_kwargs", {}).get("cubic", None) is not False:
            hints.append(
                "hcp is not a cubic lattice. Pass builder_kwargs={'cubic': False} or rely on the default hcp behavior."
            )
    if "no such file" in msg or "not found" in msg:
        hints.append("Verify file paths are correct and that prior workflow steps completed successfully.")
    if tool_name in {"optimize_structure_workflow", "run_md_workflow", "analyze_trajectory_workflow"}:
        hints.append("Use returned artifact download_url links for trajectory/log/analysis files instead of regenerating files manually.")
    if "kimpy" in msg or "kim api" in msg or "openkim" in msg:
        hints.append(
            "KIM dependencies are missing. Either install kimpy/KIM API on the server or set calculator_name to 'auto', 'orb', or 'nequix' to use an available backend."
        )
    if isinstance(exc, MemoryError) or any(signal in msg for signal in oom_signals):
        hints.append(
            "The workflow likely exhausted available memory. On Render, verify the instance size or reduce system size/steps."
        )
    if "timeout" in msg or "timed out" in msg:
        hints.append(
            "The workflow timed out. Try reducing steps, using a lighter calculator, or increasing the service timeout."
        )

    return hints


def _tool_error_response(tool_name: str, exc: Exception, elapsed_ms: float, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    compact_args = _compact_kwargs(kwargs)
    error_report_filepath = _write_error_report(tool_name, exc, elapsed_ms, compact_args)
    response: Dict[str, Any] = {
        "status": "error",
        "tool_name": tool_name,
        "error": {
            "type": exc.__class__.__name__,
            "message": str(exc),
            "elapsed_ms": round(elapsed_ms, 3),
            "traceback": traceback.format_exc(),
        },
        "inputs": compact_args,
        "error_report_filepath": error_report_filepath,
        "hints": _error_hints(tool_name, kwargs, exc),
        "next_action": "Adjust tool arguments and retry this MCP tool call. Do not replace the workflow with ad-hoc code.",
    }
    return response


def _write_error_report(
    tool_name: str,
    exc: Exception,
    elapsed_ms: float,
    compact_args: Dict[str, Any],
) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_dir = Path("tool_errors")
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{tool_name}_{timestamp}.log"
    resource_snapshot = _collect_resource_snapshot()
    report_text = "\n".join(
        [
            f"tool_name: {tool_name}",
            f"timestamp_utc: {timestamp}",
            f"elapsed_ms: {elapsed_ms:.3f}",
            f"exception_type: {exc.__class__.__name__}",
            f"exception_message: {exc}",
            "resource_snapshot:",
            str(resource_snapshot),
            "inputs:",
            str(compact_args),
            "",
            "traceback:",
            traceback.format_exc(),
        ]
    )
    report_path.write_text(report_text, encoding="utf-8")
    return str(report_path.absolute())


def _collect_resource_snapshot() -> Dict[str, Any]:
    snapshot: Dict[str, Any] = {
        "pid": os.getpid(),
        "cwd": os.getcwd(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
    }
    try:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        snapshot["max_rss_kb"] = usage.ru_maxrss
        snapshot["user_time_s"] = usage.ru_utime
        snapshot["system_time_s"] = usage.ru_stime
    except Exception as exc:
        snapshot["resource_error"] = str(exc)

    meminfo_path = Path("/proc/meminfo")
    if meminfo_path.exists():
        try:
            meminfo = meminfo_path.read_text(encoding="utf-8").splitlines()
            parsed = {}
            for line in meminfo:
                if ":" not in line:
                    continue
                key, value = line.split(":", 1)
                parsed[key.strip()] = value.strip()
            snapshot["meminfo"] = parsed
        except Exception as exc:
            snapshot["meminfo_error"] = str(exc)

    return snapshot


def _run_tool(tool_name: str, impl: Callable[..., Dict], **kwargs: Any) -> Dict:
    start = perf_counter()
    compact_args = _compact_kwargs(kwargs)
    logger.info("Tool %s called with args=%s", tool_name, compact_args)
    try:
        result = impl(**kwargs)
    except Exception as exc:
        elapsed_ms = (perf_counter() - start) * 1000
        logger.exception(
            "Tool %s failed after %.1f ms with %s: %s (args=%s)",
            tool_name,
            elapsed_ms,
            exc.__class__.__name__,
            exc,
            compact_args,
        )
        return with_downloadable_artifacts(_tool_error_response(tool_name, exc, elapsed_ms, kwargs))

    elapsed_ms = (perf_counter() - start) * 1000
    logger.info("Tool %s succeeded in %.1f ms", tool_name, elapsed_ms)
    return with_downloadable_artifacts(result)


@mcp.tool()
async def build_structure_workflow(
    formula: str,
    structure_type: str = "bulk",
    crystal_system: str = "fcc",
    lattice_constant: float = 4.0,
    pbc: List[bool] = None,
    cell: Optional[List[List[float]]] = None,
    cell_size: Optional[List[float]] = None,
    output_filepath: str = "structure.extxyz",
    output_format: Optional[str] = None,
    builder_kwargs: Optional[Dict] = None,
) -> Dict:
    """Build an atomic structure and return metadata.

    Args:
        formula: Chemical formula (e.g. 'Fe', 'TiO2')
        structure_type: Type of structure
            ('bulk', 'surface', 'molecule', 'supercell', 'amorphous', 'liquid',
            'bicrystal', 'polycrystal')
        crystal_system: Crystal system for bulk ('fcc', 'bcc', 'sc', etc.)
        lattice_constant: Lattice constant in Angstroms
        pbc: Periodic boundary condition flags
        cell: Explicit 3x3 cell matrix
        cell_size: Cell lengths (a, b, c) if cell not provided
        output_filepath: Output file path for the built structure
        output_format: Output file format (optional)
        builder_kwargs: Extra builder-specific parameters

    Returns:
        Dict containing structure metadata
    """
    return _run_tool(
        "build_structure_workflow",
        build_structure_workflow_impl,
        formula=formula,
        structure_type=structure_type,
        crystal_system=crystal_system,
        lattice_constant=lattice_constant,
        pbc=pbc or [True, True, True],
        cell=cell,
        cell_size=cell_size,
        output_filepath=output_filepath,
        output_format=output_format,
        builder_kwargs=builder_kwargs,
    )


@mcp.tool()
async def analyze_structure_workflow(
    filepath: str,
    format: Optional[str] = None,
    output_dir: str = "analysis_outputs/structure",
    rdf_max: float = 10.0,
    rdf_bins: int = 200,
    coordination_cutoff: Optional[float] = None,
    coordination_factor: float = 1.2,
    plot_formats: Optional[List[str]] = None,
) -> Dict:
    """Analyze structure file and return metadata.

    Args:
        filepath: Path to structure file
        format: File format (optional, guessed from extension if not provided)

    Returns:
        Dict containing structure metadata
    """
    return _run_tool(
        "analyze_structure_workflow",
        analyze_structure_workflow_impl,
        filepath=filepath,
        format=format,
        output_dir=output_dir,
        rdf_max=rdf_max,
        rdf_bins=rdf_bins,
        coordination_cutoff=coordination_cutoff,
        coordination_factor=coordination_factor,
        plot_formats=plot_formats,
    )


@mcp.tool()
async def write_structure_workflow(
    positions: List[List[float]],
    symbols: List[str],
    cell: List[List[float]],
    filepath: str,
    format: Optional[str] = None,
) -> Dict:
    """Write structure to file and return metadata.

    Args:
        positions: Atomic positions
        symbols: Chemical symbols
        cell: Unit cell vectors
        filepath: Output file path
        format: File format (optional, guessed from extension if not provided)

    Returns:
        Dict with status and file info
    """
    return _run_tool(
        "write_structure_workflow",
        write_structure_workflow_impl,
        positions=positions,
        symbols=symbols,
        cell=cell,
        filepath=filepath,
        format=format,
    )


@mcp.tool()
async def optimize_structure_workflow(
    input_filepath: str,
    input_format: Optional[str] = None,
    output_filepath: str = "optimized.extxyz",
    output_format: Optional[str] = None,
    calculator_name: str = DEFAULT_CALCULATOR_NAME,
    max_steps: int = 50,
    fmax: float = 0.1,
    constraints: Optional[Dict] = None,
    maxstep: float = 0.04,
    alpha: float = 70.0,
) -> Dict:
    """Optimize structure using MLIP and return metadata.

    Args:
        input_filepath: Path to structure file
        input_format: File format (optional)
        output_filepath: Output file path
        output_format: Output file format (optional)
        calculator_name: Type of MLIP ('auto', 'kim', 'nequix', or 'orb'). Defaults to auto.
        max_steps: Maximum optimization steps
        fmax: Force convergence criterion
        constraints: Constraint settings (fixed atoms/cell/bonds)
        maxstep: Maximum step size for the optimizer (Angstrom)
        alpha: BFGS damping parameter

    Returns:
        Dict containing optimized structure metadata
    """
    return _run_tool(
        "optimize_structure_workflow",
        optimize_structure_workflow_impl,
        input_filepath=input_filepath,
        input_format=input_format,
        output_filepath=output_filepath,
        output_format=output_format,
        calculator_name=calculator_name,
        max_steps=max_steps,
        fmax=fmax,
        constraints=constraints,
        maxstep=maxstep,
        alpha=alpha,
    )


@mcp.tool()
async def single_point_workflow(
    input_filepath: str,
    input_format: Optional[str] = None,
    calculator_name: str = DEFAULT_CALCULATOR_NAME,
) -> Dict:
    """Compute single-point energy, forces, and stress (if periodic)."""
    return _run_tool(
        "single_point_workflow",
        single_point_workflow_impl,
        input_filepath=input_filepath,
        input_format=input_format,
        calculator_name=calculator_name,
    )


@mcp.tool()
async def run_md_workflow(
    input_filepath: str,
    input_format: Optional[str] = None,
    output_trajectory_filepath: str = "md.extxyz",
    output_format: Optional[str] = None,
    log_filepath: str = "md.log",
    summary_filepath: str = "md_summary.txt",
    calculator_name: str = DEFAULT_CALCULATOR_NAME,
    integrator: str = "velocityverlet",
    timestep_fs: float = 1.0,
    temperature_K: float = 300.0,
    steps: int = 100,
    friction: float = 0.02,
    taut: float = 100.0,
    trajectory_interval: int = 1,
) -> Dict:
    """Run molecular dynamics workflow and return outputs.

    Integrator options:
        - velocityverlet / nve
        - langevin / nvt-langevin
        - nvt / nvt-berendsen
    """
    return _run_tool(
        "run_md_workflow",
        run_md_workflow_impl,
        input_filepath=input_filepath,
        input_format=input_format,
        output_trajectory_filepath=output_trajectory_filepath,
        output_format=output_format,
        log_filepath=log_filepath,
        summary_filepath=summary_filepath,
        calculator_name=calculator_name,
        integrator=integrator,
        timestep_fs=timestep_fs,
        temperature_K=temperature_K,
        steps=steps,
        friction=friction,
        taut=taut,
        trajectory_interval=trajectory_interval,
    )


@mcp.tool()
async def analyze_trajectory_workflow(
    filepath: str,
    format: Optional[str] = None,
    output_dir: str = "analysis_outputs/trajectory",
    timestep_fs: float = 1.0,
    rdf_max: float = 10.0,
    rdf_bins: int = 200,
    rdf_stride: int = 1,
    plot_formats: Optional[List[str]] = None,
) -> Dict:
    """Analyze a trajectory and return analysis artifacts."""
    return _run_tool(
        "analyze_trajectory_workflow",
        analyze_trajectory_workflow_impl,
        filepath=filepath,
        format=format,
        output_dir=output_dir,
        timestep_fs=timestep_fs,
        rdf_max=rdf_max,
        rdf_bins=rdf_bins,
        rdf_stride=rdf_stride,
        plot_formats=plot_formats,
    )


@mcp.tool()
async def autocorrelation_workflow(
    filepath: str,
    format: Optional[str] = None,
    output_dir: str = "analysis_outputs/autocorrelation",
    timestep_fs: float = 1.0,
    max_lag: Optional[int] = None,
    plot_formats: Optional[List[str]] = None,
) -> Dict:
    """Autocorrelation workflow for VACF and diffusion."""
    return _run_tool(
        "autocorrelation_workflow",
        autocorrelation_workflow_impl,
        filepath=filepath,
        format=format,
        output_dir=output_dir,
        timestep_fs=timestep_fs,
        max_lag=max_lag,
        plot_formats=plot_formats,
    )


async def build_structure(
    formula: str,
    structure_type: str = "bulk",
    crystal_system: str = "fcc",
    lattice_constant: float = 4.0,
    pbc: List[bool] = None,
    cell: Optional[List[List[float]]] = None,
    cell_size: Optional[List[float]] = None,
    output_filepath: str = "structure.extxyz",
    output_format: Optional[str] = None,
    builder_kwargs: Optional[Dict] = None,
) -> Dict:
    """Deprecated: use build_structure_workflow instead."""
    return await build_structure_workflow(
        formula=formula,
        structure_type=structure_type,
        crystal_system=crystal_system,
        lattice_constant=lattice_constant,
        pbc=pbc,
        cell=cell,
        cell_size=cell_size,
        output_filepath=output_filepath,
        output_format=output_format,
        builder_kwargs=builder_kwargs,
    )


@mcp.tool()
async def read_structure_file(filepath: str, format: Optional[str] = None) -> Dict:
    """Deprecated: use analyze_structure_workflow instead."""
    return await analyze_structure_workflow(filepath=filepath, format=format)


async def write_structure_file(
    positions: List[List[float]],
    symbols: List[str],
    cell: List[List[float]],
    filepath: str,
    format: Optional[str] = None,
) -> Dict:
    """Deprecated: use write_structure_workflow instead."""
    return await write_structure_workflow(
        positions=positions,
        symbols=symbols,
        cell=cell,
        filepath=filepath,
        format=format,
    )


async def optimize_with_mlip(
    input_filepath: str,
    input_format: Optional[str] = None,
    output_filepath: str = "optimized.extxyz",
    output_format: Optional[str] = None,
    calculator_name: str = DEFAULT_CALCULATOR_NAME,
    max_steps: int = 50,
    fmax: float = 0.1,
    constraints: Optional[Dict] = None,
) -> Dict:
    """Deprecated: use optimize_structure_workflow instead."""
    return await optimize_structure_workflow(
        input_filepath=input_filepath,
        input_format=input_format,
        output_filepath=output_filepath,
        output_format=output_format,
        calculator_name=calculator_name,
        max_steps=max_steps,
        fmax=fmax,
        constraints=constraints,
    )


@mcp.tool()
async def create_download_artifact(filepath: str) -> Dict:
    """Create a downloadable artifact URL for an existing file path."""
    return _run_tool("create_download_artifact", lambda filepath: {"filepath": filepath}, filepath=filepath)


if __name__ == "__main__":
    mcp.run()
