# ⚛️ MCP Atomic Toolkit

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-Streamable%20HTTP-7A3EFF)](https://modelcontextprotocol.io/)
[![tests](https://github.com/XirtamEsrevni/mcp-atomictoolkit/actions/workflows/tests.yml/badge.svg)](https://github.com/XirtamEsrevni/mcp-atomictoolkit/actions/workflows/tests.yml)

> [!NOTE]
> This project is under active development. Interfaces and behavior may evolve.

A FastMCP server for **atomistic modeling workflows** powered by ASE, pymatgen, and modern ML interatomic potentials.

It gives MCP clients a practical toolkit for:
- building structures,
- running geometry optimization + molecular dynamics,
- analyzing structures/trajectories,
- and downloading generated artifacts (data + plots).

---

## ✨ Why this repo

If you need atomistic workflows exposed as MCP tools (instead of hand-wiring scripts), this project gives you:

- **ready-to-call MCP tools** for common simulation tasks,
- **file-first outputs** that are easy to inspect/reuse,
- **artifact download URLs** so clients don’t need binary blobs in chat context,
- **deployment-ready HTTP app** with health and server-card endpoints.

---

## 🚀 Features

- **MCP-native workflows** via FastMCP tools
- **Structure generation**: bulk, surface, molecule, supercell, amorphous, liquid, bicrystal, polycrystal
- **Optimization workflows** with MLIPs (`kim` default, `nequix`/`orb` supported)
- **Molecular dynamics** workflows (Velocity Verlet, Langevin, NVT Berendsen)
- **Analysis outputs**:
  - RDF + coordination stats
  - MSD + thermodynamic trends
  - VACF + diffusion (Green-Kubo)
- **Downloadable artifacts** (`xyz`, `extxyz`, `cif`, `traj`, `png`, `svg`, `csv`, `dat`, ...)
- **Registry-friendly endpoints** (`/healthz`, server card, Streamable HTTP root)

---

## ⚡ Quick Start

### 1) Requirements

- Python **3.11+**

### 2) Install

Core install does **not** require the OpenKIM C++ API:

```bash
pip install -r requirements.txt
```

or:

```bash
pip install -e .
```

OpenKIM (`kimpy`) is optional. It compiles against the system KIM API, so a default install used to fail on machines without `libkim-api`.

To enable the KIM calculator:

```bash
# Debian/Ubuntu
sudo apt-get install -y libkim-api-dev pkg-config

pip install -e ".[kim]"
```

macOS (Homebrew): `brew install openkim-models kim-api` then `pip install -e ".[kim]"`.

Without the extra, use `calculator_name='auto'`, `'orb'`, or `'nequix'`. Runtime code already falls back when KIM is missing.

### 3) Run locally

```bash
uvicorn mcp_atomictoolkit.http_app:app --host 0.0.0.0 --port 10000
```

Alternative:

```bash
python main.py
```

STDIO mode (for desktop MCP clients):

```bash
python -m mcp_atomictoolkit.mcp_server
```

> [!IMPORTANT]
> STDIO transports must keep stdout clean for JSON-RPC. Avoid `print()` or logging to stdout
> when running the server in STDIO mode.

### 4) Smoke check

```bash
curl -s http://localhost:10000/healthz
```

Expected response:

```json
{"status":"ok"}
```

---

## 🧰 Tooling Overview

Main MCP tools exposed by the server:

- `build_structure_workflow`
- `analyze_structure_workflow`
- `write_structure_workflow`
- `optimize_structure_workflow`
- `single_point_workflow`
- `run_md_workflow`
- `analyze_trajectory_workflow`
- `autocorrelation_workflow`

Legacy aliases are also included for backward compatibility.

---

## 🌐 Endpoints

- `POST /` — primary MCP Streamable HTTP endpoint
- `GET /healthz` — health check
- `GET /docs` — lightweight documentation (README)
- `GET /.well-known/mcp/server-card.json` — MCP server card metadata
- `GET /artifacts/{artifact_id}/{filename}` — artifact download route
- `/sse/` — compatibility alias path mounted to the MCP app

---

## 📦 Deployment

### Render

`render.yaml` is included and ready to use.

Default start command:

```bash
uvicorn mcp_atomictoolkit.http_app:app --host 0.0.0.0 --port $PORT
```

### Docker

The image installs `libkim-api-dev` and the optional `[kim]` extra.

```bash
docker build -t mcp-atomictoolkit .
docker run --rm -p 7860:7860 mcp-atomictoolkit
```

---

## 🗂️ Project Structure

```text
src/mcp_atomictoolkit/
  mcp_server.py          # FastMCP tool definitions
  http_app.py            # Starlette app + routing/endpoints
  workflows/core.py      # High-level workflow orchestration
  analysis/              # Structure/trajectory/VACF analysis logic
  structure_operations.py
  optimizers.py
  md_runner.py
  artifact_store.py      # Download artifact registration + URLs
```

---

## 🧪 Workflow Notes (for MCP clients)

### Structure building coverage

`build_structure_workflow` supports:

- **bulk** (ASE `bulk`)
- **surface** (ASE `surface`)
- **molecule** (ASE `molecule`)
- **supercell** (multiplication of a base structure)
- **amorphous/liquid** (random packed structures)
- **bicrystal** and **polycrystal** (grain stacking/rotation)

For **interfaces, doped structures, adsorbates, or custom slabs**, prefer:

1. Generate the structure with ASE/pymatgen (or an external builder), then
2. Use `write_structure_workflow` to persist the final geometry for downstream steps.

This ensures MCP callers can still handle advanced structures even when a specialized
builder is required.

### Builder kwargs cheat sheet

Common `builder_kwargs` for `build_structure_workflow`:

- **surface**: `indices`, `layers`, `vacuum`
- **supercell**: `size`, `base_structure_type`, `base_crystal_system`, `base_lattice_constant`, `base_kwargs`
- **amorphous/liquid**: `num_atoms`, `box_length`, `relax`, `relax_steps`, `relax_fmax`
- **bicrystal**: `grain_size`, `interface_axis`, `rotation_angle`, `rotation_axis`, `interface_gap`
- **polycrystal**: `num_grains`, `grain_size`, `rotation_angle`

### Optimization options

`optimize_structure_workflow` exposes:

- `max_steps`, `fmax` (convergence)
- `maxstep`, `alpha` (BFGS step/damping controls)
- `constraints` (`fixed_atoms`, `fixed_bonds`, `fixed_cell`)

### Single-point calculations

`single_point_workflow` computes **energy**, **forces**, and **stress** (if periodic)
without modifying the structure, making it suitable for quick evaluations.

### MD integrators / ensembles

`run_md_workflow` supports:

- `velocityverlet` / `nve` (NVE)
- `langevin` / `nvt-langevin` (NVT)
- `nvt` / `nvt-berendsen` (NVT)

Tune `temperature_K`, `friction`, and `taut` to control thermostat behavior.

---

## 📈 GitHub Pulse

### Star history

[![Star History Chart](https://api.star-history.com/svg?repos=XirtamEsrevni/mcp-atomictoolkit&type=Date)](https://star-history.com/#XirtamEsrevni/mcp-atomictoolkit&Date)

---

## 🤝 Contributing

- Keep outputs file-based and artifact-friendly.
- When adding tools, usually update both:
  - `workflows/core.py`
  - `mcp_server.py`
- Preserve `http_app.py` compatibility behavior unless intentionally changing deployment contracts.

---

## 📄 License

MIT — see `LICENSE`.
