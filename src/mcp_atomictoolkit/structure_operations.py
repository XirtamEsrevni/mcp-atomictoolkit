"""Core structure manipulation operations using ASE."""

from typing import Dict
from ase import Atoms
from ase.build import bulk, molecule, surface
from pymatgen.core import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer


def create_structure(
    formula: str,
    structure_type: str = "bulk",
    crystal_system: str = "fcc",
    lattice_constant: float = 4.0,
    **kwargs,
) -> Atoms:
    """Create atomic structure based on type and parameters.

    Args:
        formula: Chemical formula
        structure_type: Type of structure ('bulk', 'surface', 'molecule')
        crystal_system: Crystal system for bulk
        lattice_constant: Lattice constant in Angstroms
        **kwargs: Additional parameters for specific structure types

    Returns:
        ASE Atoms object
    """
    if structure_type == "bulk":
        atoms = bulk(
            formula, crystal_system, a=lattice_constant, cubic=kwargs.get("cubic", True)
        )
    elif structure_type == "molecule":
        atoms = molecule(formula)
    elif structure_type == "surface":
        bulk_atoms = bulk(formula, crystal_system, a=lattice_constant)
        atoms = surface(
            bulk_atoms,
            indices=kwargs.get("indices", (1, 1, 1)),
            layers=kwargs.get("layers", 4),
            vacuum=kwargs.get("vacuum", 10.0),
        )
    else:
        raise ValueError(f"Unknown structure type: {structure_type}")

    return atoms


def manipulate_structure(atoms: Atoms, operation: str, **kwargs) -> Atoms:
    """Perform structure manipulation operations.

    Args:
        atoms: Input structure
        operation: Operation to perform
        **kwargs: Operation-specific parameters

    Returns:
        Modified structure
    """
    if operation == "rotate":
        atoms.rotate(
            kwargs.get("angle", 90),
            kwargs.get("axis", "z"),
            center=kwargs.get("center", "COP"),
        )
    elif operation == "translate":
        atoms.translate(kwargs.get("vector", [0, 0, 1]))
    elif operation == "strain":
        strain = kwargs.get("strain", 0.02)
        atoms.cell *= 1 + strain
        atoms.wrap()
    elif operation == "supercell":
        atoms = atoms * kwargs.get("size", (2, 2, 2))
    else:
        raise ValueError(f"Unknown operation: {operation}")

    return atoms


def get_structure_info(atoms: Atoms) -> Dict:
    """Get detailed information about structure.

    Args:
        atoms: Input structure

    Returns:
        Dictionary with structure information
    """
    # Convert to pymatgen structure for analysis
    lattice = atoms.cell.array
    species = atoms.get_chemical_symbols()
    coords = atoms.get_scaled_positions()
    structure = Structure(lattice, species, coords)

    # Analyze symmetry
    analyzer = SpacegroupAnalyzer(structure)

    return {
        "formula": atoms.get_chemical_formula(),
        "num_atoms": len(atoms),
        "volume": atoms.get_volume(),
        "cell_lengths": atoms.cell.lengths().tolist(),
        "cell_angles": atoms.cell.angles().tolist(),
        "pbc": atoms.pbc.tolist(),
        "spacegroup": analyzer.get_space_group_symbol(),
        "crystal_system": analyzer.get_crystal_system(),
        "point_group": analyzer.get_point_group_symbol(),
    }
