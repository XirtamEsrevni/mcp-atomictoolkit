from pathlib import Path

import numpy as np
import pytest
from ase import Atoms

from mcp_atomictoolkit.analysis import autocorrelation


def _frame_with_velocity(v: float) -> Atoms:
    atoms = Atoms("H", positions=[[0, 0, 0]])
    atoms.set_velocities([[v, 0.0, 0.0]])
    return atoms


def test_compute_vacf_known_signal() -> None:
    velocities = np.array([
        [[1.0, 0.0, 0.0]],
        [[2.0, 0.0, 0.0]],
        [[3.0, 0.0, 0.0]],
    ])
    vacf = autocorrelation._compute_vacf(velocities, max_lag=2)
    assert vacf.tolist() == pytest.approx([14 / 3, 4.0, 3.0])


def test_analyze_vacf_rejects_empty_trajectory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(autocorrelation, "_read_trajectory", lambda *_args, **_kwargs: [])
    with pytest.raises(ValueError, match="No frames"):
        autocorrelation.analyze_vacf("dummy.traj")


def test_analyze_vacf_rejects_missing_velocities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        autocorrelation,
        "_read_trajectory",
        lambda *_args, **_kwargs: [Atoms("H", positions=[[0, 0, 0]])],
    )

    original_get_velocities = Atoms.get_velocities

    def _no_velocities(self):
        return None

    monkeypatch.setattr(Atoms, "get_velocities", _no_velocities)
    with pytest.raises(ValueError, match="does not contain velocities"):
        autocorrelation.analyze_vacf("dummy.traj")
    monkeypatch.setattr(Atoms, "get_velocities", original_get_velocities)


def test_analyze_vacf_writes_expected_outputs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    frames = [_frame_with_velocity(v) for v in (1.0, 0.5, 0.25)]
    monkeypatch.setattr(autocorrelation, "_read_trajectory", lambda *_args, **_kwargs: frames)

    result = autocorrelation.analyze_vacf(
        "trajectory.xyz",
        output_dir=str(tmp_path),
        timestep_fs=2.0,
        plot_formats=["PNG"],
    )

    assert result["summary"]["num_frames"] == 3
    assert Path(result["outputs"]["vacf_csv"]).exists()
    assert Path(result["outputs"]["diffusion_csv"]).exists()
    assert Path(result["outputs"]["vacf_plot_png"]).exists()
