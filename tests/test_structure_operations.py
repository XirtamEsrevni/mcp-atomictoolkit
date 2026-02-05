import hypothesis.strategies as st
import pytest
from ase import Atoms
from hypothesis import given

from mcp_atomictoolkit.structure_operations import (
    _assign_species,
    _resolve_cell,
    create_structure,
    get_structure_info,
    manipulate_structure,
)


def test_resolve_cell_prefers_explicit_cell() -> None:
    cell = [[1, 0, 0], [0, 2, 0], [0, 0, 3]]
    resolved = _resolve_cell(cell=cell, cell_size=(4, 4, 4), default_size=9)
    assert resolved.tolist() == cell


def test_resolve_cell_raises_for_invalid_cell_size() -> None:
    with pytest.raises(ValueError, match="cell_size"):
        _resolve_cell(cell=None, cell_size=(1, 2), default_size=5)


@given(num_atoms=st.integers(min_value=1, max_value=50))
def test_assign_species_matches_requested_atom_count(num_atoms: int) -> None:
    symbols = _assign_species("Cu2Zn", num_atoms=num_atoms)
    assert len(symbols) == num_atoms
    assert set(symbols).issubset({"Cu", "Zn"})


def test_create_structure_unknown_type_raises() -> None:
    with pytest.raises(ValueError, match="Unknown structure type"):
        create_structure("Cu", structure_type="nonsense")


def test_create_bulk_and_supercell_sizes() -> None:
    bulk = create_structure("Cu", structure_type="bulk", crystal_system="fcc")
    supercell = create_structure(
        "Cu",
        structure_type="supercell",
        base_structure_type="bulk",
        size=(2, 1, 1),
    )

    assert len(supercell) == 2 * len(bulk)


def test_create_molecule_allows_custom_cell() -> None:
    atoms = create_structure("H2O", structure_type="molecule", cell_size=(10, 10, 10))
    assert atoms.cell.lengths().tolist() == pytest.approx([10, 10, 10])


def test_manipulate_structure_translate_and_supercell() -> None:
    atoms = Atoms("H", positions=[[0, 0, 0]], cell=[5, 5, 5], pbc=[True, True, True])
    moved = manipulate_structure(atoms.copy(), "translate", vector=[1, 2, 3])
    expanded = manipulate_structure(atoms.copy(), "supercell", size=(2, 1, 1))

    assert moved.positions[0].tolist() == pytest.approx([1, 2, 3])
    assert len(expanded) == 2


def test_manipulate_unknown_operation_raises() -> None:
    atoms = Atoms("H", positions=[[0, 0, 0]])
    with pytest.raises(ValueError, match="Unknown operation"):
        manipulate_structure(atoms, "bad")


def test_get_structure_info_non_periodic_has_no_symmetry() -> None:
    atoms = Atoms("H2", positions=[[0, 0, 0], [0, 0, 0.74]], cell=[10, 10, 10], pbc=[False, False, False])
    info = get_structure_info(atoms)

    assert info["num_atoms"] == 2
    assert info["spacegroup"] is None
