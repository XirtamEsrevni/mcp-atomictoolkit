from pathlib import Path
from typing import List, Dict, Optional
from fastmcp import FastMCP
from ase import Atoms
from structure_operations import (
    create_structure,
    get_structure_info,
)
from optimizers import optimize_structure
from io_handlers import read_structure, write_structure

mcp = FastMCP(
    "atomictoolkit",
    description="ASE and more tools",
)


@mcp.tool()
async def build_structure(
    formula: str,
    structure_type: str = "bulk",
    crystal_system: str = "fcc",
    lattice_constant: float = 4.0,
) -> Dict:
    """Build an atomic structure.

    Args:
        formula: Chemical formula (e.g. 'Fe', 'TiO2')
        structure_type: Type of structure ('bulk', 'surface', 'molecule')
        crystal_system: Crystal system for bulk ('fcc', 'bcc', 'sc', etc.)
        lattice_constant: Lattice constant in Angstroms

    Returns:
        Dict containing structure data
    """
    structure = create_structure(
        formula, structure_type, crystal_system, lattice_constant
    )
    return {
        "positions": structure.positions.tolist(),
        "cell": structure.cell.tolist(),
        "symbols": structure.get_chemical_symbols(),
        "info": get_structure_info(structure),
    }


@mcp.tool()
async def read_structure_file(filepath: str, format: Optional[str] = None) -> Dict:
    """Read structure from file.

    Args:
        filepath: Path to structure file
        format: File format (optional, guessed from extension if not provided)

    Returns:
        Dict containing structure data
    """
    structure = read_structure(filepath, format)
    return {
        "positions": structure.positions.tolist(),
        "cell": structure.cell.tolist(),
        "symbols": structure.get_chemical_symbols(),
        "info": get_structure_info(structure),
    }


@mcp.tool()
async def write_structure_file(
    positions: List[List[float]],
    symbols: List[str],
    cell: List[List[float]],
    filepath: str,
    format: Optional[str] = None,
) -> Dict:
    """Write structure to file.

    Args:
        positions: Atomic positions
        symbols: Chemical symbols
        cell: Unit cell vectors
        filepath: Output file path
        format: File format (optional, guessed from extension if not provided)

    Returns:
        Dict with status and file info
    """
    structure = Atoms(symbols=symbols, positions=positions, cell=cell, pbc=True)
    write_structure(structure, filepath, format)
    return {
        "status": "success",
        "filepath": str(Path(filepath).absolute()),
        "format": format or Path(filepath).suffix[1:],
    }


@mcp.tool()
async def optimize_with_mlip(
    positions: List[List[float]],
    symbols: List[str],
    cell: List[List[float]],
    mlip_type: str = "orb",
    max_steps: int = 50,
    fmax: float = 0.1,
) -> Dict:
    """Optimize structure using MLIP.

    Args:
        positions: Atomic positions
        symbols: Chemical symbols
        cell: Unit cell vectors
        mlip_type: Type of MLIP ('orb' or 'mace')
        max_steps: Maximum optimization steps
        fmax: Force convergence criterion

    Returns:
        Dict containing optimized structure
    """
    structure = Atoms(symbols=symbols, positions=positions, cell=cell, pbc=True)

    optimized = optimize_structure(
        structure, mlip_type=mlip_type, max_steps=max_steps, fmax=fmax
    )

    return {
        "positions": optimized.positions.tolist(),
        "cell": optimized.cell.tolist(),
        "symbols": optimized.get_chemical_symbols(),
        "info": get_structure_info(optimized),
        "converged": optimized.info.get("optimization_converged", False),
        "steps": optimized.info.get("optimization_steps", 0),
        "final_fmax": optimized.info.get("optimization_fmax", None),
    }


if __name__ == "__main__":
    mcp.run()
