"""High-level workflows for MCP Atomic Toolkit."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Sequence

from ase import Atoms

from mcp_atomictoolkit.analysis.autocorrelation import analyze_vacf
from mcp_atomictoolkit.analysis.structure import analyze_structure
from mcp_atomictoolkit.analysis.trajectory import analyze_trajectory
from mcp_atomictoolkit.calculators import DEFAULT_CALCULATOR_NAME, resolve_calculator
from mcp_atomictoolkit.io_handlers import read_structure, write_structure
from mcp_atomictoolkit.md_runner import run_md
from mcp_atomictoolkit.optimizers import optimize_structure
from mcp_atomictoolkit.structure_operations import create_structure, get_structure_info


def build_structure_workflow(
    formula: str,
    structure_type: str = "bulk",
    crystal_system: str = "fcc",
    lattice_constant: float = 4.0,
    pbc: Sequence[bool] = (True, True, True),
    cell: Optional[List[List[float]]] = None,
    cell_size: Optional[Sequence[float]] = None,
    output_filepath: str = "structure.extxyz",
    output_format: Optional[str] = None,
    builder_kwargs: Optional[Dict] = None,
) -> Dict:
    """Build an atomic structure, write to disk, and return metadata."""
    structure = create_structure(
        formula,
        structure_type,
        crystal_system,
        lattice_constant,
        pbc=pbc,
        cell=cell,
        cell_size=cell_size,
        **(builder_kwargs or {}),
    )
    write_structure(structure, output_filepath, output_format)
    info = get_structure_info(structure)
    symmetry_summary = {
        "spacegroup": info.get("spacegroup"),
        "crystal_system": info.get("crystal_system"),
        "point_group": info.get("point_group"),
    }
    return {
        "filepath": str(Path(output_filepath).absolute()),
        "format": output_format or Path(output_filepath).suffix[1:],
        "formula": info.get("formula"),
        "num_atoms": info.get("num_atoms"),
        "cell": info.get("cell"),
        "symmetry": symmetry_summary,
    }


def analyze_structure_workflow(
    filepath: str,
    format: Optional[str] = None,
    output_dir: str = "analysis_outputs/structure",
    rdf_max: float = 10.0,
    rdf_bins: int = 200,
    coordination_cutoff: Optional[float] = None,
    coordination_factor: float = 1.2,
    plot_formats: Optional[Sequence[str]] = None,
) -> Dict:
    """Analyze a structure file and return metadata and analysis artifacts."""
    analysis = analyze_structure(
        filepath=filepath,
        format=format,
        output_dir=output_dir,
        rdf_max=rdf_max,
        rdf_bins=rdf_bins,
        coordination_cutoff=coordination_cutoff,
        coordination_factor=coordination_factor,
        plot_formats=plot_formats,
    )
    structure = read_structure(filepath, format)
    return {
        "filepath": str(Path(filepath).absolute()),
        "format": format or Path(filepath).suffix[1:],
        "info": get_structure_info(structure),
        "symbols": structure.get_chemical_symbols(),
        "analysis": analysis,
    }


def write_structure_workflow(
    positions: List[List[float]],
    symbols: List[str],
    cell: List[List[float]],
    filepath: str,
    format: Optional[str] = None,
) -> Dict:
    """Write a structure to disk and return metadata."""
    structure = Atoms(symbols=symbols, positions=positions, cell=cell, pbc=True)
    write_structure(structure, filepath, format)
    return {
        "status": "success",
        "filepath": str(Path(filepath).absolute()),
        "format": format or Path(filepath).suffix[1:],
    }


def optimize_structure_workflow(
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
    """Optimize a structure read from disk, write results, and return metadata."""
    structure = read_structure(input_filepath, input_format)
    optimized = optimize_structure(
        structure,
        calculator_name=calculator_name,
        max_steps=max_steps,
        fmax=fmax,
        constraints=constraints,
        maxstep=maxstep,
        alpha=alpha,
    )

    write_structure(optimized, output_filepath, output_format)
    output_path = str(Path(output_filepath).absolute())

    return {
        "output_filepath": output_path,
        "converged": optimized.info.get("optimization_converged", False),
        "steps": optimized.info.get("optimization_steps", 0),
        "final_fmax": optimized.info.get("optimization_fmax", None),
        "calculator_requested": optimized.info.get("calculator_requested", calculator_name),
        "calculator_used": optimized.info.get("calculator_used", calculator_name),
        "calculator_fallbacks": optimized.info.get("calculator_fallbacks", []),
    }


def single_point_workflow(
    input_filepath: str,
    input_format: Optional[str] = None,
    calculator_name: str = DEFAULT_CALCULATOR_NAME,
) -> Dict:
    """Compute single-point energy/forces without relaxation or MD."""
    structure = read_structure(input_filepath, input_format)
    species = sorted(set(structure.get_chemical_symbols()))
    calculator, calculator_used, calculator_errors = resolve_calculator(
        calculator_name,
        species=species,
    )
    structure.calc = calculator

    energy = structure.get_potential_energy()
    forces = structure.get_forces()
    stress = None
    if all(structure.pbc):
        stress = structure.get_stress().tolist()

    return {
        "input_filepath": str(Path(input_filepath).absolute()),
        "energy": energy,
        "forces": forces.tolist(),
        "stress": stress,
        "calculator_requested": calculator_name,
        "calculator_used": calculator_used,
        "calculator_fallbacks": calculator_errors,
    }


def run_md_workflow(
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
    """Run an MD simulation and return output paths and summary stats."""
    return run_md(
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


def analyze_trajectory_workflow(
    filepath: str,
    format: Optional[str] = None,
    output_dir: str = "analysis_outputs/trajectory",
    timestep_fs: float = 1.0,
    rdf_max: float = 10.0,
    rdf_bins: int = 200,
    rdf_stride: int = 1,
    plot_formats: Optional[Sequence[str]] = None,
) -> Dict:
    """Analyze a trajectory and return analysis artifacts."""
    return analyze_trajectory(
        filepath=filepath,
        format=format,
        output_dir=output_dir,
        timestep_fs=timestep_fs,
        rdf_max=rdf_max,
        rdf_bins=rdf_bins,
        rdf_stride=rdf_stride,
        plot_formats=plot_formats,
    )


def autocorrelation_workflow(
    filepath: str,
    format: Optional[str] = None,
    output_dir: str = "analysis_outputs/autocorrelation",
    timestep_fs: float = 1.0,
    max_lag: Optional[int] = None,
    plot_formats: Optional[Sequence[str]] = None,
) -> Dict:
    """Compute VACF/autocorrelation analysis and diffusion coefficients."""
    return analyze_vacf(
        filepath=filepath,
        format=format,
        output_dir=output_dir,
        timestep_fs=timestep_fs,
        max_lag=max_lag,
        plot_formats=plot_formats,
    )
