# Hosting Atomic Toolkit MCP

A public MCP server needs a process that speaks Streamable HTTP. Paid always-on boxes are nicer. A sleeping free web service plus a GitHub Actions ping also works if you accept cold starts and 512 MB RAM.

## Recommended no-card path: Render free web + Actions ping

Render free web services do not need a credit card. They sleep after **15 minutes** idle and wake on the next HTTP request (often 30–60 seconds). RAM is **512 MB**, so use the lite `Dockerfile` only.

1. Merge or deploy branch `feature/free-tier-and-atomistic-recipes`.
2. Sign in at [render.com](https://render.com) with GitHub. No card.
3. **New → Web Service** → this repo → Docker.
4. Instance type **Free**. Health check path `/healthz`. Port `7860`.
5. After the first deploy you get `https://YOUR-SERVICE.onrender.com`.

Confirm:

```bash
curl -sS https://YOUR-SERVICE.onrender.com/healthz
```

Then in the GitHub repo: **Settings → Secrets and variables → Actions**

- Secret `HEALTHCHECK_URL` = `https://YOUR-SERVICE.onrender.com/healthz`
- Optional variable `KEEPALIVE_MODE`:
  - `wake` (default) — 3-minute retry loop, good for cold start
  - `keep` — single short ping. Combined with the 10-minute cron this usually prevents Render sleep

Workflow: `.github/workflows/keepalive.yml`

- runs every 10 minutes from **main** (GitHub cron only fires on the default branch)
- also has **Run workflow** so you can pre-warm before a session

Keeping one Render free service awake 24/7 uses almost the whole **750 instance-hour** monthly budget. That is fine for a single MCP. A second always-awake service will exhaust the month and Render will suspend both.

MCP clients often time out on the first call after sleep. Either click **Run workflow** first, or hit `/healthz` in a browser and wait for 200 before starting a long job.

```json
{
  "mcpServers": {
    "atomictoolkit": {
      "url": "https://YOUR-SERVICE.onrender.com/"
    }
  }
}
```

## Hugging Face

Docker Spaces now require a paid plan to *create*. Skip HF unless you already have PRO.

## blitz.cloud

No card, sleeps after 2 hours, wakes on the next visit. Needs a **public amd64 Docker Hub image** that runs as non-root. 512 MB shared. Possible later if someone publishes `mcp-atomictoolkit` to Docker Hub; Render from this GitHub repo is simpler today.

## Image flavors

| File | What you get | Use when |
| --- | --- | --- |
| `Dockerfile` | ASE, pymatgen, FastMCP, EMT | Public free host |
| `Dockerfile.full` | + OpenKIM + Orb + Nequix | Paid box with ≥8 GB RAM |

```bash
docker build -t mcp-atomictoolkit:lite .
docker build -f Dockerfile.full -t mcp-atomictoolkit:full .
```

On the lite image, `calculator_name='auto'` falls through to EMT for Al/Cu/Ag/Au/Ni/Pd/Pt. Other chemistries need `[mlip]` or `[kim]`. Keep MD `steps` and supercells small. Prefer `steps<=50`.

## Oracle Always Free ARM

Works if you will put a card on file for identity checks. 2 OCPU / 12 GB in 2026. Not needed if Render + the wake workflow is enough.


## Render memory profile

Render free web is about 512 MB. The server detects that host automatically (`RENDER=true`) and also honors `MEMORY_PROFILE=render`.

On that profile the MCP process will:

- force calculators to EMT (`auto` never tries Orb/Nequix/KIM)
- cap MD at 40 steps and relaxations at 25 steps
- reject amorphous/liquid/polycrystal/bicrystal builders
- reject trajectory analysis and VACF
- reject supercells whose repeat product is greater than 8
- refuse more than 32 atoms written from coordinates

`GET /healthz` includes `memory_profile`, so the wake workflow still sees `200` without running a job. `list_workspace_capabilities_workflow` includes the same limits.

Set `MEMORY_PROFILE=full` only on a box with real RAM.
