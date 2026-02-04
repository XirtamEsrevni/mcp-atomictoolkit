"""Autocorrelation workflows."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib.pyplot as plt
import numpy as np
from ase import Atoms
from ase.io import read


def _write_json(data: Dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def _write_csv(rows: List[List], header: List[str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def _read_trajectory(filepath: str, format: Optional[str]) -> List[Atoms]:
    frames = read(filepath, format=format, index=":")
    if not isinstance(frames, list):
        return [frames]
    return frames


def _compute_vacf(velocities: np.ndarray, max_lag: int) -> np.ndarray:
    n_frames = velocities.shape[0]
    vacf = np.zeros(max_lag + 1)
    for lag in range(max_lag + 1):
        v0 = velocities[: n_frames - lag]
        vt = velocities[lag:]
        dot = np.sum(v0 * vt, axis=2)
        vacf[lag] = float(np.mean(dot))
    return vacf


def analyze_vacf(
    filepath: str,
    format: Optional[str] = None,
    output_dir: str = "analysis_outputs/autocorrelation",
    timestep_fs: float = 1.0,
    max_lag: Optional[int] = None,
) -> Dict:
    """Compute VACF and diffusion coefficients from a trajectory."""
    frames = _read_trajectory(filepath, format)
    if not frames:
        raise ValueError("No frames found in trajectory")

    velocities = []
    for atoms in frames:
        vel = atoms.get_velocities()
        if vel is None:
            raise ValueError("Trajectory does not contain velocities required for VACF")
        velocities.append(vel)

    vel_array = np.array(velocities)
    n_frames = vel_array.shape[0]
    max_lag = n_frames - 1 if max_lag is None else min(max_lag, n_frames - 1)

    vacf = _compute_vacf(vel_array, max_lag=max_lag)
    vacf_norm = vacf / vacf[0] if vacf[0] != 0 else vacf

    time_fs = np.arange(max_lag + 1) * timestep_fs
    dt_fs = timestep_fs
    diffusion = np.zeros_like(vacf)
    if len(vacf) > 1:
        cumulative = np.cumsum(0.5 * (vacf[:-1] + vacf[1:]) * dt_fs)
        diffusion[1:] = cumulative / 3.0

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    vacf_csv = output_path / "vacf.csv"
    _write_csv(
        [[float(t), float(v), float(vn)] for t, v, vn in zip(time_fs, vacf, vacf_norm)],
        ["time_fs", "vacf", "vacf_normalized"],
        vacf_csv,
    )

    vacf_plot = output_path / "vacf.png"
    plt.figure()
    plt.plot(time_fs, vacf_norm, color="teal")
    plt.xlabel("Time (fs)")
    plt.ylabel("Normalized VACF")
    plt.title("Velocity autocorrelation function")
    plt.tight_layout()
    plt.savefig(vacf_plot)
    plt.close()

    diffusion_csv = output_path / "diffusion.csv"
    _write_csv(
        [[float(t), float(d)] for t, d in zip(time_fs, diffusion)],
        ["time_fs", "diffusion_A2_per_fs"],
        diffusion_csv,
    )

    diffusion_plot = output_path / "diffusion.png"
    plt.figure()
    plt.plot(time_fs, diffusion, color="darkorange")
    plt.xlabel("Time (fs)")
    plt.ylabel("D (Å$^2$/fs)")
    plt.title("Diffusion coefficient (Green-Kubo)")
    plt.tight_layout()
    plt.savefig(diffusion_plot)
    plt.close()

    summary = {
        "input_filepath": str(Path(filepath).absolute()),
        "format": format or Path(filepath).suffix[1:],
        "num_frames": n_frames,
        "timestep_fs": timestep_fs,
        "vacf_initial": float(vacf[0]),
        "diffusion_final_A2_per_fs": float(diffusion[-1]) if diffusion.size else 0.0,
    }

    summary_path = output_path / "vacf_summary.json"
    _write_json(summary, summary_path)

    return {
        "summary": summary,
        "outputs": {
            "summary_json": str(summary_path.absolute()),
            "vacf_csv": str(vacf_csv.absolute()),
            "vacf_plot": str(vacf_plot.absolute()),
            "diffusion_csv": str(diffusion_csv.absolute()),
            "diffusion_plot": str(diffusion_plot.absolute()),
        },
        "notes": "Computed VACF and diffusion coefficient using Green-Kubo integration.",
    }
