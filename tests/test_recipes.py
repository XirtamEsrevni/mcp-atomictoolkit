from pathlib import Path

from mcp_atomictoolkit.workflows.core import build_structure_workflow
from mcp_atomictoolkit.workflows.recipes import (
    add_adsorbate_workflow,
    convert_structure_workflow,
    equation_of_state_workflow,
    standardize_cell_workflow,
    vacancy_formation_workflow,
)


def test_convert_standardize_eos_vacancy_adsorbate(tmp_path: Path) -> None:
    cu = tmp_path / "cu.extxyz"
    build_structure_workflow(
        "Cu",
        structure_type="bulk",
        crystal_system="fcc",
        lattice_constant=3.6,
        output_filepath=str(cu),
    )
    cif = convert_structure_workflow(
        input_filepath=str(cu),
        output_filepath=str(tmp_path / "cu.cif"),
    )
    assert cif["format"] == "cif"
    assert Path(cif["filepath"]).exists()

    std = standardize_cell_workflow(
        input_filepath=str(cu),
        output_filepath=str(tmp_path / "cu_std.cif"),
        cell_type="conventional",
    )
    assert std["num_atoms"] >= 1
    assert std["spacegroup"]

    eos = equation_of_state_workflow(
        input_filepath=str(cu),
        calculator_name="emt",
        strain_max=0.04,
        n_points=5,
        plot_filepath=str(tmp_path / "eos.png"),
    )
    assert eos["calculator_used"] == "emt"
    assert eos["volume0_A3"] > 0
    assert Path(eos["plot_filepath"]).exists()

    vac = vacancy_formation_workflow(
        input_filepath=str(cu),
        calculator_name="emt",
        index=0,
        vacancy_filepath=str(tmp_path / "vac.extxyz"),
    )
    assert vac["n_atoms_perfect"] == 4
    assert vac["formation_energy_eV"] == vac["formation_energy_eV"]

    slab = tmp_path / "slab.extxyz"
    build_structure_workflow(
        "Cu",
        structure_type="surface",
        crystal_system="fcc",
        lattice_constant=3.6,
        output_filepath=str(slab),
        builder_kwargs={"indices": [1, 1, 1], "layers": 3, "vacuum": 8.0},
    )
    ads = add_adsorbate_workflow(
        input_filepath=str(slab),
        adsorbate="H",
        output_filepath=str(tmp_path / "cu_h.extxyz"),
        height=1.5,
        position="ontop",
    )
    assert ads["num_atoms"] >= 2
