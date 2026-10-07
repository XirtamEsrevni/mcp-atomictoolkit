import time

import pytest
from ase.build import bulk
from ase.io import write

from mcp_atomictoolkit.jobs import JobStore
from mcp_atomictoolkit.workflows import phonons as phonon_mod
from mcp_atomictoolkit.workflows.phonons import submit_phonon_job


def test_render_rejects_phonons(monkeypatch):
    monkeypatch.setenv("MEMORY_PROFILE", "render")
    with pytest.raises(ValueError, match="disabled on the Render"):
        submit_phonon_job("cu.extxyz")


def test_phonon_job_writes_dos(tmp_path, monkeypatch):
    atoms = bulk("Cu", "fcc", a=3.6)
    structure = tmp_path / "cu.extxyz"
    write(structure, atoms)
    monkeypatch.setenv("JOBS_DIR", str(tmp_path / "jobs"))
    monkeypatch.setenv("MEMORY_PROFILE", "full")
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.setattr(phonon_mod, "STORE", JobStore(tmp_path / "jobs"))

    submitted = submit_phonon_job(
        str(structure),
        calculator_name="emt",
        supercell=[1, 1, 1],
        kpts=[1, 1, 1],
        npts=10,
    )
    job_id = submitted["job_id"]
    final = None
    for _ in range(60):
        final = phonon_mod.STORE.get(job_id)
        if final["status"] in {"completed", "failed", "cancelled"}:
            break
        time.sleep(0.25)
    assert final["status"] == "completed", final.get("error")
    assert final["result"]["n_modes"] > 0
    assert job_id in final["result"]["dos_filepath"]
