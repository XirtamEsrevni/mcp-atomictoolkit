from typing import List, Dict, Optional
from fastmcp import FastMCP

from mcp_atomictoolkit.workflows.core import (
    analyze_structure_workflow as analyze_structure_workflow_impl,
    analyze_trajectory_workflow as analyze_trajectory_workflow_impl,
    autocorrelation_workflow as autocorrelation_workflow_impl,
    build_structure_workflow as build_structure_workflow_impl,
    optimize_structure_workflow as optimize_structure_workflow_impl,
    run_md_workflow as run_md_workflow_impl,
    write_structure_workflow as write_structure_workflow_impl,
)

mcp = FastMCP(
    "atomictoolkit",
    description="ASE and more tools",
)


@mcp.tool()
async def build_structure_workflow(
    formula: str,
    structure_type: str = "bulk",
    crystal_system: str = "fcc",
    lattice_constant: float = 4.0,
) -> Dict:
    """Build an atomic structure and return metadata.

    Args:
        formula: Chemical formula (e.g. 'Fe', 'TiO2')
        structure_type: Type of structure ('bulk', 'surface', 'molecule')
        crystal_system: Crystal system for bulk ('fcc', 'bcc', 'sc', etc.)
        lattice_constant: Lattice constant in Angstroms

    Returns:
        Dict containing structure metadata
    """
    return build_structure_workflow_impl(
        formula=formula,
        structure_type=structure_type,
        crystal_system=crystal_system,
        lattice_constant=lattice_constant,
    )


@mcp.tool()
async def analyze_structure_workflow(
    filepath: str, format: Optional[str] = None
) -> Dict:
    """Analyze structure file and return metadata.

    Args:
        filepath: Path to structure file
        format: File format (optional, guessed from extension if not provided)

    Returns:
        Dict containing structure metadata
    """
    return analyze_structure_workflow_impl(filepath=filepath, format=format)


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
    return write_structure_workflow_impl(
        positions=positions,
        symbols=symbols,
        cell=cell,
        filepath=filepath,
        format=format,
    )


@mcp.tool()
async def optimize_structure_workflow(
    positions: List[List[float]],
    symbols: List[str],
    cell: List[List[float]],
    mlip_type: str = "orb",
    max_steps: int = 50,
    fmax: float = 0.1,
) -> Dict:
    """Optimize structure using MLIP and return metadata.

    Args:
        positions: Atomic positions
        symbols: Chemical symbols
        cell: Unit cell vectors
        mlip_type: Type of MLIP ('orb' or 'mace')
        max_steps: Maximum optimization steps
        fmax: Force convergence criterion

    Returns:
        Dict containing optimized structure metadata
    """
    return optimize_structure_workflow_impl(
        positions=positions,
        symbols=symbols,
        cell=cell,
        mlip_type=mlip_type,
        max_steps=max_steps,
        fmax=fmax,
    )


@mcp.tool()
async def run_md_workflow(*args, **kwargs) -> Dict:
    """Run molecular dynamics workflow (not yet implemented)."""
    return run_md_workflow_impl(*args, **kwargs)


@mcp.tool()
async def analyze_trajectory_workflow(*args, **kwargs) -> Dict:
    """Analyze trajectory workflow (not yet implemented)."""
    return analyze_trajectory_workflow_impl(*args, **kwargs)


@mcp.tool()
async def autocorrelation_workflow(*args, **kwargs) -> Dict:
    """Autocorrelation workflow (not yet implemented)."""
    return autocorrelation_workflow_impl(*args, **kwargs)


@mcp.tool()
async def build_structure(
    formula: str,
    structure_type: str = "bulk",
    crystal_system: str = "fcc",
    lattice_constant: float = 4.0,
) -> Dict:
    """Deprecated: use build_structure_workflow instead."""
    return await build_structure_workflow(
        formula=formula,
        structure_type=structure_type,
        crystal_system=crystal_system,
        lattice_constant=lattice_constant,
    )


@mcp.tool()
async def read_structure_file(filepath: str, format: Optional[str] = None) -> Dict:
    """Deprecated: use analyze_structure_workflow instead."""
    return await analyze_structure_workflow(filepath=filepath, format=format)


@mcp.tool()
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


@mcp.tool()
async def optimize_with_mlip(
    positions: List[List[float]],
    symbols: List[str],
    cell: List[List[float]],
    mlip_type: str = "orb",
    max_steps: int = 50,
    fmax: float = 0.1,
) -> Dict:
    """Deprecated: use optimize_structure_workflow instead."""
    return await optimize_structure_workflow(
        positions=positions,
        symbols=symbols,
        cell=cell,
        mlip_type=mlip_type,
        max_steps=max_steps,
        fmax=fmax,
    )


if __name__ == "__main__":
    mcp.run()
