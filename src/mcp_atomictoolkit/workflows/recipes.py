"""Higher-level atomistic recipes used by the MCP workspace."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Sequence

from ase.build import add_adsorbate, molecule, surface
from ase.eos import EquationOfState
from ase.io import write as ase_write
from pymatgen.io.ase import AseAtomsAdaptor
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

from mcp_atomictoolkit.calculators import DEFAULT_CALCULATOR_NAME, resolve_calculator
from mcp_atomictoolkit.io_handlers import get_supported_formats, read_structure, write_structure
from mcp_atomictoolkit.structure_operations import get_structure_info, manipulate_structure


def convert_structure_workflow(
    input_filepath: str,
    output_filepath: str,
    input_format: Optional[str] = None,
    output_format: Optional[str] = None,
) -> Dict:
    """Convert a structure between ASE-supported formats."""
    atoms = read_structure(input_filepath, input_format)
    write_structure(atoms, output_filepath, output_format)
    info = get_structure_info(atoms)
    return {
        "status": "success",
        "input_filepath": str(Path(input_filepath).absolute()),
        "filepath": str(Path(output_filepath).absolute()),
        "format": output_format or Path(output_filepath).suffix[1:],
        "supported_formats": get_supported_formats(),
        "num_atoms": info.get("num_atoms"),
        "formula": info.get("formula"),
    }


def standardize_cell_workflow(
    input_filepath: str,
    input_format: Optional[str] = None,
    output_filepath: str = "standardized.cif",
    output_format: Optional[str] = None,
    cell_type: str = "conventional",
    symprec: float = 0.1,
) -> Dict:
    """Rewrite a crystal to a primitive or conventional standard cell."""
    atoms = read_structure(input_filepath, input_format)
    structure = AseAtomsAdaptor.get_structure(atoms)
    analyzer = SpacegroupAnalyzer(structure, symprec=symprec)
    requested = cell_type.strip().lower()
    if requested in {"primitive", "prim"}:
        standardized = analyzer.get_primitive_standard_structure()
    elif requested in {"conventional", "conv", "standard"}:
        standardized = analyzer.get_conventional_standard_structure()
    else:
        raise ValueError("cell_type must be 'primitive' or 'conventional'")
    out_atoms = AseAtomsAdaptor.get_atoms(standardized)
    write_structure(out_atoms, output_filepath, output_format)
    info = get_structure_info(out_atoms)
    return {
        "status": "success",
        "cell_type": requested,
        "spacegroup": analyzer.get_space_group_symbol(),
        "filepath": str(Path(output_filepath).absolute()),
        "num_atoms": info.get("num_atoms"),
        "formula": info.get("formula"),
        "cell": info.get("cell"),
    }


def equation_of_state_workflow(
    input_filepath: str,
    input_format: Optional[str] = None,
    calculator_name: str = DEFAULT_CALCULATOR_NAME,
    strain_max: float = 0.06,
    n_points: int = 5,
    eos_type: str = "birchmurnaghan",
    plot_filepath: str = "eos.png",
) -> Dict:
    """Fit an equation of state and return equilibrium volume and bulk modulus."""
    if n_points < 3:
        raise ValueError("n_points must be at least 3")
    atoms = read_structure(input_filepath, input_format)
    species = sorted(set(atoms.get_chemical_symbols()))
    calculator, calculator_used, calculator_errors = resolve_calculator(
        calculator_name, species=species
    )
    strains = [(-strain_max + 2 * strain_max * i / (n_points - 1)) for i in range(n_points)]
    volumes: List[float] = []
    energies: List[float] = []
    for strain in strains:
        sample = atoms.copy()
        sample.set_cell(atoms.cell * (1.0 + strain), scale_atoms=True)
        sample.calc = calculator
        volumes.append(float(sample.get_volume()))
        energies.append(float(sample.get_potential_energy()))
    eos = EquationOfState(volumes, energies, eos=eos_type)
    volume0, energy0, bulk_modulus = eos.fit()
    Path(plot_filepath).parent.mkdir(parents=True, exist_ok=True)
    eos.plot(filename=plot_filepath)
    return {
        "status": "success",
        "eos_type": eos_type,
        "volume0_A3": float(volume0),
        "energy0_eV": float(energy0),
        "bulk_modulus_eV_A3": float(bulk_modulus),
        "samples": [
            {"strain": strain, "volume_A3": volume, "energy_eV": energy}
            for strain, volume, energy in zip(strains, volumes, energies)
        ],
        "plot_filepath": str(Path(plot_filepath).absolute()),
        "calculator_requested": calculator_name,
        "calculator_used": calculator_used,
        "calculator_fallbacks": calculator_errors,
    }


def vacancy_formation_workflow(
    input_filepath: str,
    input_format: Optional[str] = None,
    calculator_name: str = DEFAULT_CALCULATOR_NAME,
    index: int = 0,
    vacancy_filepath: str = "vacancy.extxyz",
) -> Dict:
    """Estimate unrelaxed vacancy formation energy: E_def - E_perfect*(N-1)/N."""
    perfect = read_structure(input_filepath, input_format)
    if len(perfect) < 2:
        raise ValueError("vacancy formation needs at least two atoms")
    species = sorted(set(perfect.get_chemical_symbols()))
    calculator, calculator_used, calculator_errors = resolve_calculator(
        calculator_name, species=species
    )
    perfect.calc = calculator
    energy_perfect = float(perfect.get_potential_energy())
    defect = manipulate_structure(perfect, "vacancy", index=index)
    defect.calc = calculator
    energy_defect = float(defect.get_potential_energy())
    write_structure(defect, vacancy_filepath)
    n_atoms = len(perfect)
    formation = energy_defect - energy_perfect * (n_atoms - 1) / n_atoms
    return {
        "status": "success",
        "index": index,
        "n_atoms_perfect": n_atoms,
        "energy_perfect_eV": energy_perfect,
        "energy_defect_eV": energy_defect,
        "formation_energy_eV": float(formation),
        "vacancy_filepath": str(Path(vacancy_filepath).absolute()),
        "calculator_requested": calculator_name,
        "calculator_used": calculator_used,
        "calculator_fallbacks": calculator_errors,
    }


def add_adsorbate_workflow(
    input_filepath: str,
    adsorbate: str,
    input_format: Optional[str] = None,
    output_filepath: str = "adsorbed.extxyz",
    height: float = 1.8,
    position: str = "ontop",
    make_slab: bool = False,
    miller_indices: Sequence[int] = (1, 1, 1),
    layers: int = 3,
    vacuum: float = 10.0,
) -> Dict:
    """Add an adsorbate atom or molecule onto a surface."""
    atoms = read_structure(input_filepath, input_format)
    if make_slab:
        atoms = surface(atoms, indices=tuple(miller_indices), layers=layers, vacuum=vacuum)
    try:
        adsorbate_atoms = molecule(adsorbate)
    except Exception:
        adsorbate_atoms = adsorbate
    add_adsorbate(atoms, adsorbate_atoms, height=height, position=position)
    write_structure(atoms, output_filepath)
    info = get_structure_info(atoms)
    return {
        "status": "success",
        "adsorbate": adsorbate,
        "position": position,
        "height": height,
        "filepath": str(Path(output_filepath).absolute()),
        "num_atoms": info.get("num_atoms"),
        "formula": info.get("formula"),
    }
