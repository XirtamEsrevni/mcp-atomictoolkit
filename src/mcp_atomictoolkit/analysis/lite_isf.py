"""Lightweight intermediate scattering function. Pure numpy, fits Render."""

from __future__ import annotations

from typing import Dict, Optional

import numpy as np
from ase.io import read


def lite_intermediate_scattering(
    input_filepath: str,
    q_magnitude: float = 2.0,
    dt_fs: float = 5.0,
    max_lag: int = 50,
    input_format: Optional[str] = None,
) -> Dict:
    """Spherically averaged intermediate scattering function F(q, t).

    Approximation using a single |q| shell and random orientations.
    Not a replacement for dynasor; suitable for short trajectories on Render.
    """
    if q_magnitude <= 0:
        raise ValueError("q_magnitude must be positive")
    if dt_fs <= 0:
        raise ValueError("dt_fs must be positive")
    if max_lag < 1:
        raise ValueError("max_lag must be at least 1")

    frames = read(input_filepath, format=input_format, index=":")
    if not isinstance(frames, list):
        frames = [frames]
    if len(frames) < 2:
        raise ValueError("Need at least 2 frames")

    # Use positions relative to first frame cell
    positions = [f.get_positions() for f in frames]
    n_frames = len(positions)
    n_atoms = len(positions[0])
    lag_max = min(max_lag, n_frames - 1)

    # Sample a few random q directions at fixed |q|
    rng = np.random.default_rng(0)
    n_dirs = 8
    directions = rng.normal(size=(n_dirs, 3))
    directions /= np.linalg.norm(directions, axis=1, keepdims=True)
    q_vectors = directions * q_magnitude

    # F(q, t) ≈ <exp(i q · (r(t) - r(0)))>
    isf = np.zeros(lag_max + 1)
    counts = np.zeros(lag_max + 1)
    for q in q_vectors:
        # Phase for each frame: shape (n_frames, n_atoms)
        phases = np.array([np.exp(1j * positions[i] @ q) for i in range(n_frames)])
        for lag in range(lag_max + 1):
            # Average over time origins and atoms
            corr = phases[lag:] * np.conj(phases[: n_frames - lag])
            isf[lag] += np.real(corr.mean())
            counts[lag] += 1
    isf /= np.maximum(counts, 1)

    times_fs = np.arange(lag_max + 1) * dt_fs
    return {
        "q_magnitude_per_A": float(q_magnitude),
        "dt_fs": float(dt_fs),
        "n_frames": n_frames,
        "n_atoms": n_atoms,
        "times_fs": times_fs.tolist(),
        "F_qt": isf.tolist(),
        "note": "Lite approximation. Use dynasor off-Render for production spectra.",
    }
