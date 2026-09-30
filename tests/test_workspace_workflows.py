from pathlib import Path

from ase.build import bulk

from mcp_atomictoolkit.structure_operations import get_structure_info, manipulate_structure
from mcp_atomictoolkit.workflows.core import (
    build_structure_workflow,
    estimate_elastic_workflow,
    import_structure_workflow,
    list_workspace_capabilities_workflow,
    manipulate_structure_workflow,
    relax_and_md_workflow,
)


def test_list_workspace_capabilities_includes_emt_and_npt() -> None:
    caps = list_workspace_capabilities_workflow()
    assert caps["default_calculator"] == "auto"
    assert "emt" in caps["auto_order"]
    assert "npt" in caps["integrators"]
    assert "vacancy" in caps["manipulate_operations"]
    assert caps["calculators"]["emt"]["available"] is True


def test_import_and_defect_edits(tmp_path: Path) -> None:
    xyz = "2\n\nCu 0 0 0\nCu 1.8 1.8 0\n"
    imported = import_structure_workflow(
        contents=xyz,
        input_format="xyz",
        output_filepath=str(tmp_path / "cu2.xyz"),
    )
    assert imported["num_atoms"] == 2

    vacant = manipulate_structure_workflow(
        input_filepath=imported["filepath"],
        operation="vacancy",
        output_filepath=str(tmp_path / "vac.xyz"),
        operation_kwargs={"index": 1},
    )
    assert vacant["num_atoms"] == 1

    alloyed = manipulate_structure_workflow(
        input_filepath=imported["filepath"],
        operation="substitute",
        output_filepath=str(tmp_path / "cuag.xyz"),
        operation_kwargs={"index": 0, "symbol": "Ag"},
    )
    assert "Ag" in alloyed["formula"]

    wrapped = manipulate_structure_workflow(
        input_filepath=imported["filepath"],
        operation="wrap",
        output_filepath=str(tmp_path / "wrap.xyz"),
    )
    assert wrapped["num_atoms"] == 2

    stuffed = manipulate_structure_workflow(
        input_filepath=imported["filepath"],
        operation="interstitial",
        output_filepath=str(tmp_path / "int.xyz"),
        operation_kwargs={"symbol": "Ni", "position": [0.9, 0.9, 0.9]},
    )
    assert stuffed["num_atoms"] == 3


def test_manipulate_does_not_mutate_input() -> None:
    atoms = bulk("Cu", "fcc", a=3.6, cubic=True)
    original = len(atoms)
    edited = manipulate_structure(atoms, "vacancy", index=0)
    assert len(atoms) == original
    assert len(edited) == original - 1
    info = get_structure_info(atoms)
    assert info["volume"] > 0


def test_elastic_and_relax_md_with_emt(tmp_path: Path) -> None:
    structure_path = tmp_path / "cu.extxyz"
    build_structure_workflow(
        "Cu",
        structure_type="bulk",
        crystal_system="fcc",
        lattice_constant=3.6,
        output_filepath=str(structure_path),
    )
    elastic = estimate_elastic_workflow(
        input_filepath=str(structure_path),
        calculator_name="emt",
    )
    assert elastic["calculator_used"] == "emt"
    assert elastic["bulk_modulus_GPa"] > 0
    assert len(elastic["samples"]) == 5

    recipe = relax_and_md_workflow(
        input_filepath=str(structure_path),
        optimized_filepath=str(tmp_path / "opt.extxyz"),
        output_trajectory_filepath=str(tmp_path / "md.extxyz"),
        log_filepath=str(tmp_path / "md.log"),
        summary_filepath=str(tmp_path / "md_summary.txt"),
        calculator_name="emt",
        max_steps=2,
        fmax=0.5,
        integrator="nvt",
        steps=2,
    )
    assert recipe["status"] == "success"
    assert recipe["md"]["calculator_used"] == "emt"
