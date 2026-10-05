# Background jobs

`run_md_workflow` blocks until MD finishes. A 100 ps run at 1 fs is 100000 steps and will outlive an agent turn.

Use:

1. `submit_md_job` with `duration_ps=100` (or `steps`). It returns `job_id` immediately.
2. Disconnect.
3. `get_job` with that `job_id` from any later MCP session on the same server process.
4. `cancel_job` stops between chunks (default 20 steps).

Jobs are JSON files under `JOBS_DIR` (default `jobs/`). They survive a new HTTP connection. They do not survive a Render sleep or a process restart, because the worker thread dies with the process.

On Render (`RENDER=true` or `MEMORY_PROFILE=render`) MD jobs are clamped to 40 steps so the 512 MB dyno is not killed. The job record says `clamped_for_host: true`. A 100 ps run needs a full-profile host.
