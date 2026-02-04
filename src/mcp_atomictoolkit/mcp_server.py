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
    pbc: List[bool] = None,
    cell: Optional[List[List[float]]] = None,
    cell_size: Optional[List[float]] = None,
    output_filepath: str = "structure.xyz",
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
    return build_structure_workflow_impl(
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
) -> Dict:
    """Analyze structure file and return metadata.

    Args:
        filepath: Path to structure file
        format: File format (optional, guessed from extension if not provided)

    Returns:
        Dict containing structure metadata
    """
    return analyze_structure_workflow_impl(
        filepath=filepath,
        format=format,
        output_dir=output_dir,
        rdf_max=rdf_max,
        rdf_bins=rdf_bins,
        coordination_cutoff=coordination_cutoff,
        coordination_factor=coordination_factor,
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
    return write_structure_workflow_impl(
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
    output_filepath: str = "optimized.xyz",
    output_format: Optional[str] = None,
    calculator_name: str = "orb",
    max_steps: int = 50,
    fmax: float = 0.1,
    constraints: Optional[Dict] = None,
) -> Dict:
    """Optimize structure using MLIP and return metadata.

    Args:
        input_filepath: Path to structure file
        input_format: File format (optional)
        output_filepath: Output file path
        output_format: Output file format (optional)
        calculator_name: Type of MLIP ('orb' or 'mace')
        max_steps: Maximum optimization steps
        fmax: Force convergence criterion
        constraints: Constraint settings (fixed atoms/cell/bonds)

    Returns:
        Dict containing optimized structure metadata
    """
    return optimize_structure_workflow_impl(
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
async def run_md_workflow(
    input_filepath: str,
    input_format: Optional[str] = None,
    output_trajectory_filepath: str = "md.traj",
    output_format: Optional[str] = None,
    log_filepath: str = "md.log",
    summary_filepath: str = "md_summary.txt",
    integrator: str = "velocityverlet",
    timestep_fs: float = 1.0,
    temperature_K: float = 300.0,
    steps: int = 100,
    friction: float = 0.02,
    taut: float = 100.0,
    trajectory_interval: int = 1,
) -> Dict:
    """Run molecular dynamics workflow and return outputs."""
    return run_md_workflow_impl(
        input_filepath=input_filepath,
        input_format=input_format,
        output_trajectory_filepath=output_trajectory_filepath,
        output_format=output_format,
        log_filepath=log_filepath,
        summary_filepath=summary_filepath,
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
) -> Dict:
    """Analyze a trajectory and return analysis artifacts."""
    return analyze_trajectory_workflow_impl(
        filepath=filepath,
        format=format,
        output_dir=output_dir,
        timestep_fs=timestep_fs,
        rdf_max=rdf_max,
        rdf_bins=rdf_bins,
        rdf_stride=rdf_stride,
    )


@mcp.tool()
async def autocorrelation_workflow(
    filepath: str,
    format: Optional[str] = None,
    output_dir: str = "analysis_outputs/autocorrelation",
    timestep_fs: float = 1.0,
    max_lag: Optional[int] = None,
) -> Dict:
    """Autocorrelation workflow for VACF and diffusion."""
    return autocorrelation_workflow_impl(
        filepath=filepath,
        format=format,
        output_dir=output_dir,
        timestep_fs=timestep_fs,
        max_lag=max_lag,
    )


@mcp.tool()
async def build_structure(
    formula: str,
    structure_type: str = "bulk",
    crystal_system: str = "fcc",
    lattice_constant: float = 4.0,
    pbc: List[bool] = None,
    cell: Optional[List[List[float]]] = None,
    cell_size: Optional[List[float]] = None,
    output_filepath: str = "structure.xyz",
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
    input_filepath: str,
    input_format: Optional[str] = None,
    output_filepath: str = "optimized.xyz",
    output_format: Optional[str] = None,
    calculator_name: str = "orb",
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


if __name__ == "__main__":
    mcp.run()
