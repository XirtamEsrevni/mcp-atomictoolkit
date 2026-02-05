from pathlib import Path

import numpy as np
import pytest
from ase import Atoms

from mcp_atomictoolkit.analysis import trajectory


def test_extract_energy_prefers_info_keys() -> None:
    atoms = Atoms("H", positions=[[0, 0, 0]])
    atoms.info["energy"] = -1.2
    assert trajectory._extract_energy(atoms) == -1.2


def test_extract_energy_falls_back_to_nan_when_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    atoms = Atoms("H", positions=[[0, 0, 0]])

    def _boom():
        raise RuntimeError("no calculator")

    monkeypatch.setattr(atoms, "get_potential_energy", _boom)
    assert np.isnan(trajectory._extract_energy(atoms))


def test_analyze_trajectory_rejects_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(trajectory, "_read_trajectory", lambda *_args, **_kwargs: [])
    with pytest.raises(ValueError, match="No frames"):
        trajectory.analyze_trajectory("dummy.xyz")


def test_analyze_trajectory_outputs_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    f0 = Atoms("H2", positions=[[0, 0, 0], [0, 0, 0.74]], cell=[5, 5, 5], pbc=[True] * 3)
    f1 = Atoms("H2", positions=[[0.1, 0, 0], [0, 0.1, 0.74]], cell=[5, 5, 5], pbc=[True] * 3)
    f0.info["potential_energy"] = -1.0
    f1.info["potential_energy"] = -0.9
    monkeypatch.setattr(trajectory, "_read_trajectory", lambda *_args, **_kwargs: [f0, f1])

    result = trajectory.analyze_trajectory(
        "traj.xyz",
        output_dir=str(tmp_path),
        rdf_bins=10,
        rdf_stride=1,
        plot_formats=["PnG"],
    )

    assert result["summary"]["num_frames"] == 2
    assert Path(result["outputs"]["msd_csv"]).exists()
    assert Path(result["outputs"]["rdf_time_json"]).exists()
    assert Path(result["outputs"]["thermo_plot_png"]).exists()
