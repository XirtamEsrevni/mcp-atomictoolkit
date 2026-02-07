"""Core structure manipulation operations using ASE."""

from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
from ase import Atoms
from ase.build import bulk, molecule, surface
from ase.calculators.emt import EMT
from ase.optimize import BFGS
from pymatgen.core import Composition, Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer


def _resolve_cell(
    cell: Optional[Sequence[Sequence[float]]],
    cell_size: Optional[Sequence[float]],
    default_size: float,
) -> Optional[np.ndarray]:
    if cell is not None:
        return np.array(cell, dtype=float)
    if cell_size is not None:
        if len(cell_size) != 3:
            raise ValueError("cell_size must be a sequence of length 3")
        return np.diag(np.array(cell_size, dtype=float))
    return np.diag([default_size, default_size, default_size])


def _assign_species(formula: str, num_atoms: int) -> List[str]:
    composition = Composition(formula)
    fractions = composition.fractional_composition.get_el_amt_dict()
    symbols: List[str] = []
    remaining = num_atoms
    for idx, (element, fraction) in enumerate(fractions.items()):
        if idx == len(fractions) - 1:
            count = remaining
        else:
            count = max(1, int(round(fraction * num_atoms)))
        symbols.extend([element] * count)
        remaining -= count
    if remaining > 0:
        symbols.extend([list(fractions.keys())[-1]] * remaining)
    return symbols


def _random_packed_structure(
    formula: str,
    num_atoms: int,
    cell_matrix: np.ndarray,
    pbc: Sequence[bool],
    relax: bool,
    relax_steps: int,
    relax_fmax: float,
) -> Atoms:
    symbols = _assign_species(formula, num_atoms)
    frac_positions = np.random.rand(num_atoms, 3)
    positions = frac_positions @ cell_matrix
    atoms = Atoms(symbols=symbols, positions=positions, cell=cell_matrix, pbc=pbc)
    if relax:
        atoms.calc = EMT()
        optimizer = BFGS(atoms, logfile=None)
        optimizer.run(fmax=relax_fmax, steps=relax_steps)
    return atoms


def _stack_grains(
    grain_a: Atoms,
    grain_b: Atoms,
    axis: int,
    gap: float,
    pbc: Sequence[bool],
) -> Atoms:
    axis_vector = grain_a.cell.array[axis]
    axis_length = np.linalg.norm(axis_vector)
    if axis_length == 0:
        raise ValueError("Grain cell axis length must be non-zero")
    axis_unit = axis_vector / axis_length
    translation = axis_vector + axis_unit * gap
    grain_b = grain_b.copy()
    grain_b.translate(translation)
    combined = grain_a + grain_b
    cell = grain_a.cell.array.copy()
    cell[axis] = cell[axis] + grain_b.cell.array[axis] + axis_unit * gap
    combined.set_cell(cell)
    combined.pbc = pbc
    return combined


def create_structure(
    formula: str,
    structure_type: str = "bulk",
    crystal_system: str = "fcc",
    lattice_constant: float = 4.0,
    pbc: Sequence[bool] = (True, True, True),
    cell: Optional[Sequence[Sequence[float]]] = None,
    cell_size: Optional[Sequence[float]] = None,
    **kwargs,
) -> Atoms:
    """Create atomic structure based on type and parameters.

    Args:
        formula: Chemical formula
        structure_type: Type of structure
            ('bulk', 'surface', 'molecule', 'supercell', 'amorphous', 'liquid',
            'bicrystal', 'polycrystal')
        crystal_system: Crystal system for bulk
        lattice_constant: Lattice constant in Angstroms
        pbc: Periodic boundary condition flags
        cell: Explicit cell matrix (3x3)
        cell_size: Cell lengths (a, b, c) if cell not provided
        **kwargs: Additional parameters for specific structure types

    Returns:
        ASE Atoms object
    """
    incompatible_cubic_crystals = {"hcp", "rhombohedral", "trigonal", "hexagonal"}
    requested_cubic = kwargs.get("cubic")
    default_cubic = crystal_system.lower() not in incompatible_cubic_crystals
    use_cubic = default_cubic if requested_cubic is None else bool(requested_cubic)

    if structure_type == "bulk":
        atoms = bulk(
            formula, crystal_system, a=lattice_constant, cubic=use_cubic
        )
        atoms.pbc = pbc
    elif structure_type == "molecule":
        atoms = molecule(formula)
        atoms.pbc = pbc
        if cell is not None or cell_size is not None:
            atoms.set_cell(_resolve_cell(cell, cell_size, lattice_constant * 5))
    elif structure_type == "surface":
        bulk_atoms = bulk(formula, crystal_system, a=lattice_constant)
        atoms = surface(
            bulk_atoms,
            indices=kwargs.get("indices", (1, 1, 1)),
            layers=kwargs.get("layers", 4),
            vacuum=kwargs.get("vacuum", 10.0),
        )
        atoms.pbc = pbc
    elif structure_type == "supercell":
        base_type = kwargs.get("base_structure_type", "bulk")
        base = create_structure(
            formula,
            structure_type=base_type,
            crystal_system=kwargs.get("base_crystal_system", crystal_system),
            lattice_constant=kwargs.get("base_lattice_constant", lattice_constant),
            pbc=pbc,
            cell=cell,
            cell_size=cell_size,
            **kwargs.get("base_kwargs", {}),
        )
        size = kwargs.get("size", (2, 2, 2))
        atoms = base * size
    elif structure_type in {"amorphous", "liquid"}:
        num_atoms = int(kwargs.get("num_atoms", 100))
        cell_matrix = _resolve_cell(
            cell, cell_size, kwargs.get("box_length", lattice_constant * 3)
        )
        atoms = _random_packed_structure(
            formula=formula,
            num_atoms=num_atoms,
            cell_matrix=cell_matrix,
            pbc=pbc,
            relax=bool(kwargs.get("relax", False)),
            relax_steps=int(kwargs.get("relax_steps", 100)),
            relax_fmax=float(kwargs.get("relax_fmax", 0.1)),
        )
    elif structure_type == "bicrystal":
        grain_size = kwargs.get("grain_size", (4, 4, 4))
        axis_label = kwargs.get("interface_axis", "z")
        axis_map = {"x": 0, "y": 1, "z": 2}
        axis = axis_map.get(axis_label, 2)
        grain_a = bulk(
            formula, crystal_system, a=lattice_constant, cubic=use_cubic
        )
        grain_a = grain_a * grain_size
        grain_b = grain_a.copy()
        rotation_angle = float(kwargs.get("rotation_angle", 15.0))
        rotation_axis = kwargs.get("rotation_axis", (0, 0, 1))
        grain_b.rotate(rotation_angle, rotation_axis, rotate_cell=True)
        gap = float(kwargs.get("interface_gap", 0.0))
        atoms = _stack_grains(grain_a, grain_b, axis=axis, gap=gap, pbc=pbc)
    elif structure_type == "polycrystal":
        num_grains = int(kwargs.get("num_grains", 4))
        grain_size = kwargs.get("grain_size", (3, 3, 3))
        grid = int(np.ceil(num_grains ** (1 / 3)))
        base = bulk(
            formula, crystal_system, a=lattice_constant, cubic=use_cubic
        )
        grains: List[Atoms] = []
        for idx in range(num_grains):
            grain = base * grain_size
            angle = float(kwargs.get("rotation_angle", 15.0)) * (idx + 1)
            grain.rotate(angle, (0, 0, 1), rotate_cell=True)
            shift = np.array(
                [
                    (idx % grid) * grain.cell.lengths()[0],
                    ((idx // grid) % grid) * grain.cell.lengths()[1],
                    (idx // (grid * grid)) * grain.cell.lengths()[2],
                ]
            )
            grain.translate(shift)
            grains.append(grain)
        atoms = grains[0]
        for grain in grains[1:]:
            atoms += grain
        cell_matrix = _resolve_cell(
            cell, cell_size, lattice_constant * grain_size[0] * grid
        )
        atoms.set_cell(cell_matrix)
        atoms.pbc = pbc
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

    spacegroup = None
    crystal_system = None
    point_group = None
    if all(atoms.pbc):
        structure = Structure(lattice, species, coords)
        analyzer = SpacegroupAnalyzer(structure)
        spacegroup = analyzer.get_space_group_symbol()
        crystal_system = analyzer.get_crystal_system()
        point_group = analyzer.get_point_group_symbol()

    return {
        "formula": atoms.get_chemical_formula(),
        "num_atoms": len(atoms),
        "volume": atoms.get_volume(),
        "cell": atoms.cell.array.tolist(),
        "cell_lengths": atoms.cell.lengths().tolist(),
        "cell_angles": atoms.cell.angles().tolist(),
        "pbc": atoms.pbc.tolist(),
        "spacegroup": spacegroup,
        "crystal_system": crystal_system,
        "point_group": point_group,
    }
