# Async Worker Paradigm for Long-Running MCP Tasks

## Goals and constraints

This design adds non-blocking task execution to the MCP server while keeping a **single MCP deployment boundary**.

### Functional goals
- Agents submit work and immediately regain control.
- Agents can reconnect and retrieve status, logs, progress, artifacts, and final outputs.
- Work executes through a worker pool with a queue and explicit capacity control.
- Each worker runs exactly one task at a time.

### Resilience goals
- Durable task state survives MCP server restarts.
- Worker crashes and transient disconnects are recoverable.
- Cancellation, TTL, and timeout semantics are explicit.

---

## Canonical MCP tool surface

All implementation options should expose the same MCP-facing API contract.

### `submit_task`

**Input**
```json
{
  "tool_name": "run_geometry_optimization",
  "inputs": {"structure": "...", "fmax": 0.05},
  "resources": {
    "resource_class": "cpu_standard",
    "max_runtime_s": 14400,
    "cpu": 2,
    "memory_mb": 4096,
    "scratch_mb": 4096
  },
  "ttl_s": 604800,
  "idempotency_key": "agent-session-123-opt-001",
  "priority": 5,
  "tags": ["project:screening", "model:nequix"]
}
```

**Output**
```json
{
  "task_id": "tsk_01J8WQ6JY7Q7XQ8T5Q8G2NQ2S5",
  "state": "queued",
  "queue": "cpu_standard",
  "position": 3,
  "submitted_at": "2026-02-05T12:00:00Z",
  "poll_after_ms": 2000
}
```

### `get_task_status`

**Input**
```json
{"task_id": "tsk_01J8WQ6JY7Q7XQ8T5Q8G2NQ2S5"}
```

**Output**
```json
{
  "task_id": "tsk_01J8WQ6JY7Q7XQ8T5Q8G2NQ2S5",
  "state": "running",
  "tool_name": "run_geometry_optimization",
  "attempt": 1,
  "priority": 5,
  "queue": "cpu_standard",
  "worker_id": "wrk_04",
  "submitted_at": "2026-02-05T12:00:00Z",
  "started_at": "2026-02-05T12:00:08Z",
  "updated_at": "2026-02-05T12:13:10Z",
  "heartbeat_at": "2026-02-05T12:13:09Z",
  "progress": {
    "phase": "relaxation",
    "percent": 42.5,
    "step": 170,
    "step_total": 400,
    "eta_s": 680,
    "message": "Energy decrease stable"
  },
  "cancel_requested": false,
  "timeout_at": "2026-02-05T16:00:00Z"
}
```

### `tail_task_logs`

**Input**
```json
{
  "task_id": "tsk_01J8WQ6JY7Q7XQ8T5Q8G2NQ2S5",
  "cursor": "log_000001532",
  "limit": 200
}
```

**Output**
```json
{
  "task_id": "tsk_01J8WQ6JY7Q7XQ8T5Q8G2NQ2S5",
  "lines": [
    {
      "seq": 1533,
      "ts": "2026-02-05T12:13:06.101Z",
      "stream": "stdout",
      "level": "info",
      "message": "step=170 energy=-130.202"
    }
  ],
  "next_cursor": "log_000001533",
  "truncated": false
}
```

### `list_tasks`

**Input**
```json
{
  "states": ["queued", "running", "failed"],
  "tool_name": "run_geometry_optimization",
  "tags_any": ["project:screening"],
  "submitted_after": "2026-02-01T00:00:00Z",
  "limit": 50,
  "cursor": null
}
```

### `cancel_task`

**Input**
```json
{"task_id": "tsk_01J8WQ6JY7Q7XQ8T5Q8G2NQ2S5", "reason": "user-request"}
```

**Output**
```json
{
  "task_id": "tsk_01J8WQ6JY7Q7XQ8T5Q8G2NQ2S5",
  "state": "cancel_requested",
  "acknowledged": true
}
```

### `get_task_result`

**Output**
```json
{
  "task_id": "tsk_01J8WQ6JY7Q7XQ8T5Q8G2NQ2S5",
  "state": "succeeded",
  "result": {
    "status": "success",
    "energy_ev": -130.204,
    "n_steps": 221
  },
  "artifacts": [
    {
      "artifact_id": "art_abc123",
      "name": "opt.traj",
      "kind": "trajectory",
      "size_bytes": 182393,
      "sha256": "...",
      "download_url": "https://.../artifacts/art_abc123/opt.traj",
      "expires_at": "2026-02-12T12:00:00Z"
    }
  ],
  "error": null,
  "completed_at": "2026-02-05T12:22:10Z"
}
```

---

## Durable state model

A persistent state machine should be shared across all options.

### State enum
- `queued`
- `scheduled`
- `running`
- `cancel_requested`
- `cancelling`
- `succeeded`
- `failed`
- `cancelled`
- `timed_out`
- `expired`

### Core entities

1. **tasks**
   - `task_id`, `tool_name`, `inputs_json`, `resource_class`, `priority`, `ttl_s`, `idempotency_key`
   - timestamps (`submitted_at`, `started_at`, `heartbeat_at`, `completed_at`, `expires_at`)
   - execution (`state`, `attempt`, `max_attempts`, `timeout_at`, `worker_id`, `cancel_requested`)
   - output (`result_json`, `error_json`, `metrics_json`)

2. **task_events** (append-only audit trail)
   - state transitions, worker assignment, retries, cancellations

3. **task_logs**
   - `(task_id, seq, ts, stream, level, line)` for cursor-based tailing

4. **artifacts**
   - metadata + immutable file references

5. **workers**
   - `worker_id`, `resource_class`, `state`, `last_heartbeat`, `current_task_id`

### Idempotency
- `submit_task` stores `(idempotency_key, tool_name, caller_identity_scope)` unique index.
- Duplicate submission returns existing task (never creates a second task).

### Timeouts and heartbeats
- Worker heartbeat every `N` seconds while running.
- Scheduler watchdog marks task `failed` or `queued` for retry if heartbeat is stale.
- Hard timeout transitions `running -> timed_out`, with process termination.

### Retries
- Policy: `max_attempts`, `retry_backoff_s`, `retry_on` predicate.
- Recommended default for scientific workloads: no automatic retry unless failure is clearly transient (worker crash, host restart).

---

## Worker pool semantics

### Queues and resource classes
- `cpu_small`, `cpu_standard`, `cpu_heavy`, optional `gpu_small`.
- Each queue has max workers + queue length cap.

### One task per worker
- Worker process/thread/container obtains exclusive lease for one task.
- No shared execution within that worker until task reaches terminal state.

### Scheduling policy
- Priority first, then FIFO within equal priority.
- Optional fair-share by tag/project.

### Admission control
- Reject on queue saturation with explicit error:
  - `queue_full` (retry later)
  - or accept with bounded queue and estimated delay.

---

## Reconnect and recovery behavior

### Agent disconnects
- No impact: task continues server-side.
- Agent later calls `get_task_status`, `tail_task_logs`, `get_task_result`.

### MCP server restart
- On boot, scheduler restores queues from durable store.
- Running tasks handled via policy:
  1. If worker survives and heartbeats resume, keep `running`.
  2. If no heartbeat within grace period, mark attempt failed and requeue or terminal fail.

### Worker crash
- Heartbeat timeout detected by watchdog.
- Task transitions to retry or failed with error type `worker_lost`.

---

## Implementation options

## Option A — SQLite + local process workers (lightest single-host)

### Conceptual architecture

```text
Agent MCP Client
   |
   v
MCP API (FastMCP tools)
   |
   +--> SQLite task store (tasks/events/logs/artifacts)
   +--> Scheduler loop (in-process)
           |
           +--> Worker process pool (1 task per process)
                     |
                     +--> Tool runner subprocess (per task)
   +--> Artifact/log files on local disk
```

### Suggested software
- Python stdlib: `multiprocessing`, `subprocess`, `queue`
- Durable store: `SQLite` in WAL mode
- Optional: `APScheduler` for cleanup/TTL sweeps

### Pros
- Minimal dependencies, easiest to deploy on Render/free tier.
- Lowest memory footprint and operational complexity.

### Cons/failure modes
- Single host disk limits durability and throughput.
- SQLite write contention at higher concurrency.
- Local artifacts/logs lost on ephemeral disk resets unless persistent volume is configured.

### Best fit
- Small teams, low/medium queue depth, constrained budget.

---

## Option B — PostgreSQL-backed queue + local workers (minimal external dependency, stronger durability)

### Conceptual architecture

```text
Agent
  -> MCP API
      -> Postgres tables + advisory locks / SKIP LOCKED dequeue
      -> Scheduler + worker manager (same MCP service)
      -> Worker processes (1 task each)
      -> Local scratch + object storage for artifacts
```

### Suggested software
- Queue semantics in SQL (`SELECT ... FOR UPDATE SKIP LOCKED`)
- `asyncpg` / SQLAlchemy
- Optional object storage for artifacts (S3/R2/GCS)

### Pros
- Better durability and operational safety than SQLite.
- Good concurrency while keeping single MCP deployment boundary.

### Cons/failure modes
- Requires managed Postgres.
- More schema and lock correctness work.

### Best fit
- Production workloads needing reliable recovery and auditability.

---

## Option C — Redis + lightweight task queue library (RQ/Dramatiq/Arq)

### Conceptual architecture

```text
Agent -> MCP API tools
          -> enqueue job in Redis
          -> worker supervisor inside MCP service boundary
                 -> N worker processes, one task each
          -> status/log/result metadata in Redis (+ optional SQL mirror)
          -> artifacts in disk or object storage
```

### Suggested software
- Redis + one of:
  - `RQ` (simple, process-based)
  - `Dramatiq` (robust middleware/retries)
  - `Arq` (asyncio-friendly)

### Pros
- Very simple queue operations and good latency.
- Easier than full Celery while still robust.

### Cons/failure modes
- Redis persistence config matters (AOF/RDB).
- Need disciplined schema for logs/artifact metadata.

### Best fit
- Teams wanting straightforward operations with moderate scale.

---

## Option D — Celery + Redis/RabbitMQ (full featured)

### Conceptual architecture

```text
Agent -> MCP API
          -> Celery broker enqueue
          -> Celery workers (concurrency=1 per worker process)
          -> result backend (Redis/Postgres)
          -> MCP reads status/result and exposes tool API
```

### Pros
- Mature retries/routing/time limits/monitoring ecosystem.
- Supports advanced workflows later (chains/chords).

### Cons/failure modes
- Highest operational complexity for this use case.
- Heavier RAM/CPU overhead, less ideal on free-tier hosting.

### Best fit
- Existing Celery operators or complex workflow roadmaps.

---

## Option E — Managed job runners (cloud-native hybrid)

### Conceptual architecture

```text
Agent -> MCP API (control plane)
          -> submit cloud job (Cloud Run Jobs / AWS Batch / Azure Container Apps Jobs)
          -> store task metadata in DB
          -> MCP polls provider APIs for status/log links
          -> artifacts in object storage with signed URLs
```

### Pros
- Strong isolation and elasticity.
- No local worker lifecycle management.

### Cons/failure modes
- Higher cost floor and cloud coupling.
- Moves execution outside host even if MCP remains single logical server.

### Best fit
- Bursty heavy compute, strict isolation, cloud budget available.

---

## Log streaming and artifacts

### Logs
- Append logs as structured records (`seq`, `timestamp`, `stream`, `level`, `line`).
- `tail_task_logs` uses cursor-based pagination; clients poll for incremental lines.
- Optional: chunked compressed log blobs for old tasks.

### Artifacts
- Intermediate + final files written under `tasks/<task_id>/`.
- Register immutable artifact metadata with hash and size.
- Retrieval patterns:
  - local URL from MCP app (`/artifacts/{artifact_id}/{filename}`)
  - or object store signed URL (`expires_at`).

### Security
- Validate task ownership/scope before revealing logs/results/artifacts.
- Never expose arbitrary filesystem paths.
- Prefer opaque IDs and signed links.

---

## Operational comparison (quick view)

| Option | Dependencies | Durability | Complexity | Free-tier friendliness | Recommended use |
|---|---|---|---|---|---|
| A: SQLite + processes | very low | medium (single disk) | low | excellent | MVP / constrained host |
| B: Postgres queue | medium | high | medium | good | production single-host control plane |
| C: Redis + RQ/Dramatiq | medium | medium-high | medium | good | balanced simplicity and scale |
| D: Celery | high | high | high | fair | advanced workflow ecosystems |
| E: Managed jobs | medium-high | high | medium-high | poor-fair | bursty heavy compute with cloud ops |

---

## Recommended clean architecture for this repository

For this MCP server, the cleanest viable path is:

1. **Phase 1 (now): Option A**
   - SQLite WAL + local worker processes + persistent artifacts directory.
   - Add canonical MCP async tools without breaking existing direct tools.
   - Keep worker concurrency configurable (default small).

2. **Phase 2 (production hardening): Option B or C**
   - If stronger durability/audit needed: Postgres queue (B).
   - If simpler queue ergonomics desired: Redis + Dramatiq/RQ (C).

### Why this recommendation
- Preserves a single-server architecture.
- Minimal resource overhead for Render-like constrained environments.
- Provides immediate non-blocking semantics and robust recovery primitives.
- Leaves straightforward migration path without changing MCP tool contracts.

---

## Suggested implementation checklist

1. Define DB schema and task state machine.
2. Add `submit_task`, `get_task_status`, `tail_task_logs`, `list_tasks`, `cancel_task`, `get_task_result` tools.
3. Implement scheduler + worker supervisor with one-task-per-worker enforcement.
4. Add heartbeat watchdog and timeout handling.
5. Add artifact and log retention policies (`ttl_s`, cleanup cron).
6. Add idempotency and retry policy controls.
7. Add integration tests for restart recovery and cancellation race conditions.
