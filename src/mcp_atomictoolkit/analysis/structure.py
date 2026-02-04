"""Structure analysis workflows."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
from ase import Atoms
from ase.data import covalent_radii
from ase.neighborlist import NeighborList, neighbor_list

from mcp_atomictoolkit.io_handlers import read_structure
from mcp_atomictoolkit.structure_operations import get_structure_info


def _write_json(data: Dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def _write_csv(rows: List[List], header: List[str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def _compute_rdf(
    atoms: Atoms, r_max: float, bins: int
) -> Tuple[np.ndarray, np.ndarray]:
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


def _coordination_numbers(
    atoms: Atoms, cutoff: Optional[float], factor: float
) -> Tuple[List[int], Dict[str, float]]:
    if cutoff is not None:
        cutoffs = [cutoff] * len(atoms)
    else:
        cutoffs = [covalent_radii[atom.number] * factor for atom in atoms]
    neighborlist = NeighborList(cutoffs, self_interaction=False, bothways=True)
    neighborlist.update(atoms)
    coordination = []
    for idx in range(len(atoms)):
        indices, _ = neighborlist.get_neighbors(idx)
        coordination.append(len(indices))

    symbols = atoms.get_chemical_symbols()
    by_element: Dict[str, List[int]] = {}
    for symbol, coord in zip(symbols, coordination):
        by_element.setdefault(symbol, []).append(coord)

    averages = {symbol: float(np.mean(values)) for symbol, values in by_element.items()}
    return coordination, averages


def analyze_structure(
    filepath: str,
    format: Optional[str] = None,
    output_dir: str = "analysis_outputs/structure",
    rdf_max: float = 10.0,
    rdf_bins: int = 200,
    coordination_cutoff: Optional[float] = None,
    coordination_factor: float = 1.2,
) -> Dict:
    """Analyze a structure file and write summary artifacts to disk."""
    atoms = read_structure(filepath, format)
    info = get_structure_info(atoms)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    r, g_r = _compute_rdf(atoms, r_max=rdf_max, bins=rdf_bins)
    rdf_csv = output_path / "rdf.csv"
    _write_csv([[float(rv), float(gv)] for rv, gv in zip(r, g_r)], ["r", "g_r"], rdf_csv)

    rdf_plot = output_path / "rdf.png"
    plt.figure()
    plt.plot(r, g_r, color="navy")
    plt.xlabel("r (Å)")
    plt.ylabel("g(r)")
    plt.title("Radial Distribution Function")
    plt.tight_layout()
    plt.savefig(rdf_plot)
    plt.close()

    coordination, coordination_by_element = _coordination_numbers(
        atoms, cutoff=coordination_cutoff, factor=coordination_factor
    )
    coordination_csv = output_path / "coordination.csv"
    symbols = atoms.get_chemical_symbols()
    _write_csv(
        [[idx, symbol, coord] for idx, (symbol, coord) in enumerate(zip(symbols, coordination))],
        ["atom_index", "symbol", "coordination"],
        coordination_csv,
    )

    coordination_plot = output_path / "coordination_hist.png"
    plt.figure()
    plt.hist(coordination, bins=max(5, int(np.sqrt(len(coordination)))) or 5)
    plt.xlabel("Coordination number")
    plt.ylabel("Count")
    plt.title("Coordination number distribution")
    plt.tight_layout()
    plt.savefig(coordination_plot)
    plt.close()

    summary = {
        "input_filepath": str(Path(filepath).absolute()),
        "format": format or Path(filepath).suffix[1:],
        "num_atoms": info.get("num_atoms"),
        "symmetry": {
            "spacegroup": info.get("spacegroup"),
            "crystal_system": info.get("crystal_system"),
            "point_group": info.get("point_group"),
        },
        "rdf": {
            "r_max": rdf_max,
            "bins": rdf_bins,
        },
        "coordination": {
            "cutoff": coordination_cutoff,
            "factor": coordination_factor,
            "average": float(np.mean(coordination)) if coordination else 0.0,
            "by_element": coordination_by_element,
        },
    }

    summary_path = output_path / "structure_summary.json"
    _write_json(summary, summary_path)

    return {
        "summary": summary,
        "outputs": {
            "summary_json": str(summary_path.absolute()),
            "rdf_csv": str(rdf_csv.absolute()),
            "rdf_plot": str(rdf_plot.absolute()),
            "coordination_csv": str(coordination_csv.absolute()),
            "coordination_plot": str(coordination_plot.absolute()),
        },
        "notes": "Computed symmetry metadata, RDF, and coordination statistics.",
    }
