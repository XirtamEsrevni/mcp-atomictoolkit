import time

from ase.build import bulk
from ase.io import write

from mcp_atomictoolkit.jobs import JobStore
from mcp_atomictoolkit.workflows.job_workflows import steps_for_duration, submit_md_job
from mcp_atomictoolkit.workflows import job_workflows


def test_duration_ps_converts_to_steps():
    assert steps_for_duration(100.0, 1.0) == 100_000
    assert steps_for_duration(0.002, 1.0) == 2


def test_submit_md_job_can_be_polled_after_return(tmp_path, monkeypatch):
    atoms = bulk("Cu", "fcc", a=3.6)
    structure = tmp_path / "cu.extxyz"
    write(structure, atoms)
    monkeypatch.setenv("JOBS_DIR", str(tmp_path / "jobs"))
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.delenv("MEMORY_PROFILE", raising=False)
    monkeypatch.setattr(job_workflows, "STORE", JobStore(tmp_path / "jobs"))

    submitted = submit_md_job(
        input_filepath=str(structure),
        calculator_name="emt",
        integrator="nve",
        steps=2,
        timestep_fs=1.0,
        trajectory_interval=1,
        output_trajectory_filepath=str(tmp_path / "md.extxyz"),
    )
    assert submitted["status"] in {"queued", "running"}
    job_id = submitted["job_id"]

    final = None
    for _ in range(40):
        final = job_workflows.STORE.get(job_id)
        if final["status"] in {"completed", "failed", "cancelled"}:
            break
        time.sleep(0.25)
    assert final is not None
    assert final["status"] == "completed"
    assert final["result"]["summary"]["steps"] == 2
