"""High-level workflows for MCP Atomic Toolkit."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Sequence

from ase import Atoms

from mcp_atomictoolkit.io_handlers import read_structure, write_structure
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
    output_filepath: str = "structure.xyz",
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
) -> Dict:
    """Analyze a structure file and return metadata."""
    structure = read_structure(filepath, format)
    return {
        "filepath": str(Path(filepath).absolute()),
        "format": format or Path(filepath).suffix[1:],
        "info": get_structure_info(structure),
        "symbols": structure.get_chemical_symbols(),
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
    positions: List[List[float]],
    symbols: List[str],
    cell: List[List[float]],
    mlip_type: str = "orb",
    max_steps: int = 50,
    fmax: float = 0.1,
    output_filepath: Optional[str] = None,
    output_format: Optional[str] = None,
) -> Dict:
    """Optimize a structure and optionally write results to disk."""
    structure = Atoms(symbols=symbols, positions=positions, cell=cell, pbc=True)
    optimized = optimize_structure(
        structure, mlip_type=mlip_type, max_steps=max_steps, fmax=fmax
    )

    output_path = None
    if output_filepath:
        write_structure(optimized, output_filepath, output_format)
        output_path = str(Path(output_filepath).absolute())

    return {
        "info": get_structure_info(optimized),
        "symbols": optimized.get_chemical_symbols(),
        "converged": optimized.info.get("optimization_converged", False),
        "steps": optimized.info.get("optimization_steps", 0),
        "final_fmax": optimized.info.get("optimization_fmax", None),
        "output_filepath": output_path,
        "output_format": output_format
        or (Path(output_filepath).suffix[1:] if output_filepath else None),
    }


def run_md_workflow(*_args, **_kwargs) -> Dict:
    """Placeholder for MD workflow."""
    raise NotImplementedError("MD workflow is not implemented yet.")


def analyze_trajectory_workflow(*_args, **_kwargs) -> Dict:
    """Placeholder for trajectory analysis workflow."""
    raise NotImplementedError("Trajectory analysis workflow is not implemented yet.")


def autocorrelation_workflow(*_args, **_kwargs) -> Dict:
    """Placeholder for autocorrelation workflow."""
    raise NotImplementedError("Autocorrelation workflow is not implemented yet.")
