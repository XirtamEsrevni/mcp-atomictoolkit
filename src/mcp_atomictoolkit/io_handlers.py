"""File I/O operations for atomic structures."""

from pathlib import Path
from typing import Optional, Union
from ase import Atoms
from ase.io import read, write


def read_structure(filepath: Union[str, Path], format: Optional[str] = None) -> Atoms:
    """Read structure from file.

    Args:
        filepath: Path to structure file
        format: File format (optional, will guess from extension if not provided)

    Returns:
        ASE Atoms object
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    if format is None:
        format = filepath.suffix[1:]

    try:
        atoms = read(filepath, format=format)
    except Exception as e:
        raise ValueError(f"Failed to read file {filepath}: {str(e)}")

    return atoms


def write_structure(
    atoms: Atoms, filepath: Union[str, Path], format: Optional[str] = None, **kwargs
) -> None:
    """Write structure to file.

    Args:
        atoms: Structure to write
        filepath: Output file path
        format: Output format (optional, will guess from extension if not provided)
        **kwargs: Additional format-specific arguments
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    if format is None:
        format = filepath.suffix[1:]

    try:
        write(filepath, atoms, format=format, **kwargs)
    except Exception as e:
        raise ValueError(f"Failed to write file {filepath}: {str(e)}")


def get_supported_formats() -> dict:
    """Get dictionary of supported file formats and their descriptions."""
    return {
        "xyz": "XYZ format - simple Cartesian coordinates",
        "cif": "Crystallographic Information File",
        "poscar": "VASP POSCAR format",
        "json": "ASE JSON format",
        "extxyz": "Extended XYZ format with additional information",
        "traj": "ASE trajectory format",
        "pdb": "Protein Data Bank format",
        "aims": "FHI-aims geometry format",
        "xsf": "XCrySDen Structure Format",
        "cfg": "AtomEye configuration format",
    }
