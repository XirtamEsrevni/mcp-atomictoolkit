from pathlib import Path

from ase.calculators.emt import EMT

from mcp_atomictoolkit.workflows.core import (
    build_structure_workflow,
    manipulate_structure_workflow,
    optimize_structure_workflow,
    run_md_workflow,
    single_point_workflow,
    write_structure_workflow,
)


def test_build_write_manipulate_roundtrip(tmp_path: Path) -> None:
    structure_path = tmp_path / "cu.extxyz"
    built = build_structure_workflow(
        "Cu",
        structure_type="bulk",
        crystal_system="fcc",
        lattice_constant=3.6,
        output_filepath=str(structure_path),
    )
    assert built["num_atoms"] >= 1
    assert structure_path.exists()

    written = write_structure_workflow(
        positions=[[0.0, 0.0, 0.0]],
        symbols=["Cu"],
        cell=[[3.6, 0.0, 0.0], [0.0, 3.6, 0.0], [0.0, 0.0, 3.6]],
        filepath=str(tmp_path / "manual.xyz"),
    )
    assert written["status"] == "success"

    manipulated_path = tmp_path / "cu2.extxyz"
    manipulated = manipulate_structure_workflow(
        input_filepath=str(structure_path),
        operation="supercell",
        output_filepath=str(manipulated_path),
        operation_kwargs={"size": (2, 1, 1)},
    )
    assert manipulated["num_atoms"] == built["num_atoms"] * 2
    assert manipulated_path.exists()


def test_single_point_optimize_and_short_md_with_emt(tmp_path: Path) -> None:
    structure_path = tmp_path / "cu.extxyz"
    build_structure_workflow(
        "Cu",
        structure_type="bulk",
        crystal_system="fcc",
        lattice_constant=3.6,
        output_filepath=str(structure_path),
    )

    single = single_point_workflow(
        input_filepath=str(structure_path),
        calculator_name="emt",
    )
    assert single["calculator_used"] == "emt"
    assert isinstance(single["energy"], float)
    assert len(single["forces"]) >= 1

    optimized = optimize_structure_workflow(
        input_filepath=str(structure_path),
        output_filepath=str(tmp_path / "opt.extxyz"),
        calculator_name="emt",
        max_steps=2,
        fmax=0.5,
    )
    assert optimized["calculator_used"] == "emt"
    assert "converged" in optimized

    md = run_md_workflow(
        input_filepath=str(structure_path),
        output_trajectory_filepath=str(tmp_path / "md.extxyz"),
        log_filepath=str(tmp_path / "md.log"),
        summary_filepath=str(tmp_path / "md_summary.txt"),
        calculator_name="emt",
        integrator="npt",
        steps=2,
        trajectory_interval=1,
        pressure_GPa=0.0,
    )
    assert md["calculator_used"] == "emt"
    assert md["summary"]["steps"] == 2
    assert Path(md["trajectory_filepath"]).exists()
    assert isinstance(EMT(), EMT)
