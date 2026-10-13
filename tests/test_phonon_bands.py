"""Tests for the phonon band structure job."""

import os
from pathlib import Path

import pytest
from ase.build import bulk
from ase.io import write

from mcp_atomictoolkit.workflows import phonon_bands as pb


def test_phonon_bands_blocks_large_on_render(monkeypatch):
    monkeypatch.setenv("MEMORY_PROFILE", "render")
    with pytest.raises(ValueError, match="Render"):
        pb.submit_phonon_bands_job("cu.cif", supercell=[2, 2, 2])


def test_phonon_bands_rejects_bad_supercell(monkeypatch):
    monkeypatch.setenv("MEMORY_PROFILE", "full")
    with pytest.raises(ValueError, match="supercell"):
        pb.submit_phonon_bands_job("cu.cif", supercell=[3, 3, 3])


def test_phonon_bands_job_runs_on_emt_copper(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMORY_PROFILE", "full")
    monkeypatch.setenv("JOBS_DIR", str(tmp_path / "jobs"))
    atoms = bulk("Cu", "fcc", a=3.6)
    path = tmp_path / "cu.cif"
    write(path, atoms)

    result = pb.submit_phonon_bands_job(
        str(path),
        calculator_name="emt",
        supercell=[1, 1, 1],
        npoints=5,
    )
    assert result["status"] in {"queued", "running", "completed"}
    job_id = result["job_id"]

    # Poll the in-memory store until done (short job)
    from mcp_atomictoolkit.jobs import STORE
    import time

    for _ in range(60):
        job = STORE.get(job_id)
        if job and job.get("status") in {"completed", "failed", "cancelled"}:
            break
        time.sleep(0.2)
    else:
        pytest.fail("phonon bands job did not finish")

    assert job["status"] == "completed", job
    outputs = job["result"]["outputs"]
    csv_path = Path(outputs["bands_csv"])
    assert csv_path.exists()
    text = csv_path.read_text()
    assert "omega_eV" in text
    assert job["result"]["n_bands"] >= 3
