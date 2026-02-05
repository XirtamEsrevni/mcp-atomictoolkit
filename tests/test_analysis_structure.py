from pathlib import Path

import pytest
from ase import Atoms

from mcp_atomictoolkit.analysis import structure


def test_coordination_numbers_with_cutoff() -> None:
    atoms = Atoms("H2", positions=[[0, 0, 0], [0, 0, 0.74]], cell=[5, 5, 5], pbc=[False] * 3)
    coordination, by_element = structure._coordination_numbers(atoms, cutoff=1.0, factor=1.2)

    assert coordination == [1, 1]
    assert by_element["H"] == 1.0


def test_analyze_structure_creates_outputs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    atoms = Atoms("H2", positions=[[0, 0, 0], [0, 0, 0.74]], cell=[5, 5, 5], pbc=[True] * 3)
    monkeypatch.setattr(structure, "read_structure", lambda *_args, **_kwargs: atoms)
    monkeypatch.setattr(
        structure,
        "get_structure_info",
        lambda _atoms: {
            "num_atoms": 2,
            "spacegroup": "P1",
            "crystal_system": "triclinic",
            "point_group": "1",
        },
    )

    result = structure.analyze_structure(
        "input.xyz",
        output_dir=str(tmp_path),
        rdf_bins=8,
        plot_formats=["PNG"],
    )

    assert result["summary"]["num_atoms"] == 2
    assert Path(result["outputs"]["summary_json"]).exists()
    assert Path(result["outputs"]["rdf_plot_png"]).exists()
    assert Path(result["outputs"]["coordination_plot_png"]).exists()
