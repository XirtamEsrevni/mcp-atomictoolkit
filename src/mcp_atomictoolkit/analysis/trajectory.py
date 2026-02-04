"""Trajectory analysis workflows."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
from ase import Atoms
from ase.geometry import find_mic
from ase.io import read
from ase.neighborlist import neighbor_list


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


def _compute_rdf(atoms: Atoms, r_max: float, bins: int) -> Tuple[np.ndarray, np.ndarray]:
    distances = neighbor_list("d", atoms, cutoff=r_max)
    if len(distances) == 0:
        return np.linspace(0.0, r_max, bins), np.zeros(bins)
    hist, edges = np.histogram(distances, bins=bins, range=(0.0, r_max))
    r = 0.5 * (edges[1:] + edges[:-1])
    dr = edges[1] - edges[0]
    number_density = len(atoms) / atoms.get_volume() if atoms.get_volume() > 0 else 0
    shell_volume = 4.0 * np.pi * r**2 * dr
    normalization = shell_volume * number_density * len(atoms) / 2.0
    with np.errstate(divide="ignore", invalid="ignore"):
        g_r = np.where(normalization > 0, hist / normalization, 0.0)
    return r, g_r


def _extract_energy(atoms: Atoms) -> float:
    for key in ("energy", "potential_energy", "E"):
        if key in atoms.info:
            return float(atoms.info[key])
    try:
        return float(atoms.get_potential_energy())
    except Exception:
        return float("nan")


def analyze_trajectory(
    filepath: str,
    format: Optional[str] = None,
    output_dir: str = "analysis_outputs/trajectory",
    timestep_fs: float = 1.0,
    rdf_max: float = 10.0,
    rdf_bins: int = 200,
    rdf_stride: int = 1,
) -> Dict:
    """Analyze trajectory with MSD, RDF vs time, and thermodynamic stats."""
    frames = _read_trajectory(filepath, format)
    if not frames:
        raise ValueError("No frames found in trajectory")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    positions0 = frames[0].get_positions()
    msd_rows = []
    msd_values = []
    temperatures = []
    kinetic_energies = []
    potential_energies = []

    for idx, atoms in enumerate(frames):
        delta = atoms.get_positions() - positions0
        if np.any(atoms.pbc):
            delta, _ = find_mic(delta, atoms.cell, atoms.pbc)
        msd = float(np.mean(np.sum(delta**2, axis=1)))
        time_fs = idx * timestep_fs
        msd_rows.append([time_fs, msd])
        msd_values.append(msd)

        try:
            temperatures.append(float(atoms.get_temperature()))
        except Exception:
            temperatures.append(float("nan"))

        try:
            kinetic_energies.append(float(atoms.get_kinetic_energy()))
        except Exception:
            kinetic_energies.append(float("nan"))

        potential_energies.append(_extract_energy(atoms))

    msd_csv = output_path / "msd.csv"
    _write_csv(msd_rows, ["time_fs", "msd_A2"], msd_csv)

    msd_plot = output_path / "msd.png"
    plt.figure()
    plt.plot([row[0] for row in msd_rows], msd_values, color="purple")
    plt.xlabel("Time (fs)")
    plt.ylabel("MSD (Å$^2$)")
    plt.title("Mean Squared Displacement")
    plt.tight_layout()
    plt.savefig(msd_plot)
    plt.close()

    rdf_frames = []
    for idx in range(0, len(frames), max(1, rdf_stride)):
        atoms = frames[idx]
        r, g_r = _compute_rdf(atoms, r_max=rdf_max, bins=rdf_bins)
        rdf_frames.append(
            {
                "time_fs": idx * timestep_fs,
                "r": r.tolist(),
                "g_r": g_r.tolist(),
            }
        )

    rdf_time_csv = output_path / "rdf_time.csv"
    rdf_rows = []
    for frame in rdf_frames:
        for rv, gv in zip(frame["r"], frame["g_r"]):
            rdf_rows.append([frame["time_fs"], rv, gv])
    _write_csv(rdf_rows, ["time_fs", "r", "g_r"], rdf_time_csv)

    rdf_plot = output_path / "rdf_time.png"
    rdf_matrix = np.array([frame["g_r"] for frame in rdf_frames])
    plt.figure()
    if rdf_matrix.size > 0:
        plt.imshow(
            rdf_matrix,
            aspect="auto",
            origin="lower",
            extent=[0, rdf_max, rdf_frames[0]["time_fs"], rdf_frames[-1]["time_fs"]],
            cmap="viridis",
        )
        plt.colorbar(label="g(r)")
        plt.xlabel("r (Å)")
        plt.ylabel("Time (fs)")
        plt.title("RDF vs time")
    plt.tight_layout()
    plt.savefig(rdf_plot)
    plt.close()

    thermo_rows = []
    for idx, (temp, kin, pot) in enumerate(
        zip(temperatures, kinetic_energies, potential_energies)
    ):
        thermo_rows.append([idx * timestep_fs, temp, kin, pot])

    thermo_csv = output_path / "thermo.csv"
    _write_csv(
        thermo_rows,
        ["time_fs", "temperature_K", "kinetic_energy_eV", "potential_energy_eV"],
        thermo_csv,
    )

    thermo_plot = output_path / "thermo.png"
    plt.figure()
    plt.plot([row[0] for row in thermo_rows], temperatures, label="Temperature (K)")
    plt.plot([row[0] for row in thermo_rows], potential_energies, label="Potential (eV)")
    plt.xlabel("Time (fs)")
    plt.legend()
    plt.title("Thermodynamic time series")
    plt.tight_layout()
    plt.savefig(thermo_plot)
    plt.close()

    summary = {
        "input_filepath": str(Path(filepath).absolute()),
        "format": format or Path(filepath).suffix[1:],
        "num_frames": len(frames),
        "timestep_fs": timestep_fs,
        "msd_final": msd_values[-1] if msd_values else 0.0,
        "temperature_stats": {
            "mean": float(np.nanmean(temperatures)),
            "min": float(np.nanmin(temperatures)),
            "max": float(np.nanmax(temperatures)),
        },
        "potential_energy_stats": {
            "mean": float(np.nanmean(potential_energies)),
            "min": float(np.nanmin(potential_energies)),
            "max": float(np.nanmax(potential_energies)),
        },
    }

    summary_path = output_path / "trajectory_summary.json"
    _write_json(summary, summary_path)

    rdf_json = output_path / "rdf_time.json"
    _write_json({"frames": rdf_frames}, rdf_json)

    return {
        "summary": summary,
        "outputs": {
            "summary_json": str(summary_path.absolute()),
            "msd_csv": str(msd_csv.absolute()),
            "msd_plot": str(msd_plot.absolute()),
            "rdf_time_csv": str(rdf_time_csv.absolute()),
            "rdf_time_json": str(rdf_json.absolute()),
            "rdf_time_plot": str(rdf_plot.absolute()),
            "thermo_csv": str(thermo_csv.absolute()),
            "thermo_plot": str(thermo_plot.absolute()),
        },
        "notes": "Computed MSD, RDF vs time, and temperature/energy statistics.",
    }
