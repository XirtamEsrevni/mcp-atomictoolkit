import time

import pytest
from ase.build import bulk
from ase.io import write

from mcp_atomictoolkit.jobs import JobStore
from mcp_atomictoolkit.workflows import neb as neb_mod
from mcp_atomictoolkit.workflows.neb import submit_neb_job


def test_render_rejects_neb(monkeypatch):
    monkeypatch.setenv("MEMORY_PROFILE", "render")
    with pytest.raises(ValueError, match="disabled on the Render"):
        submit_neb_job("a.extxyz", "b.extxyz")


def test_neb_job_returns_a_barrier(tmp_path, monkeypatch):
    initial = bulk("Cu", "fcc", a=3.6)
    final = initial.copy()
    final.positions[0, 0] += 0.4
    start = tmp_path / "initial.extxyz"
    end = tmp_path / "final.extxyz"
    write(start, initial)
    write(end, final)
    monkeypatch.setenv("JOBS_DIR", str(tmp_path / "jobs"))
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.setenv("MEMORY_PROFILE", "full")
    monkeypatch.setattr(neb_mod, "STORE", JobStore(tmp_path / "jobs"))

    submitted = submit_neb_job(
        str(start),
        str(end),
        n_images=1,
        calculator_name="emt",
        fmax=0.5,
        max_steps=2,
    )
    job_id = submitted["job_id"]
    final_record = None
    for _ in range(40):
        final_record = neb_mod.STORE.get(job_id)
        if final_record["status"] in {"completed", "failed", "cancelled"}:
            break
        time.sleep(0.25)
    assert final_record["status"] == "completed", final_record.get("error")
    assert "barrier_eV" in final_record["result"]
    assert len(final_record["result"]["energies_eV"]) == 3
    assert job_id in final_record["result"]["trajectory_filepath"]
