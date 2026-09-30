# ⚠️ MCP Atomic Toolkit

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-Streamable%20HTTP-7A3EFF)](https://modelcontextprotocol.io/)
[![tests](https://github.com/XirtamEsrevni/mcp-atomictoolkit/actions/workflows/tests.yml/badge.svg)](https://github.com/XirtamEsrevni/mcp-atomictoolkit/actions/workflows/tests.yml)

> [!NOTE]
> This project is under active development. Interfaces and behavior may evolve.

A FastMCP server for **atomistic modeling workflows** powered by ASE, pymatgen, and modern ML interatomic potentials.

It gives MCP clients a practical toolkit for:
- building and importing structures,
- editing cells (strain, supercell) and defects (vacancy, substitution, interstitial),
- running geometry optimization + NVE/NVT/NPT molecular dynamics,
- estimating bulk modulus,
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
- **Structure import** from xyz/cif/POSCAR text
- **Edits and defects**: rotate, translate, strain, supercell, wrap, vacancy, substitute, interstitial
- **Calculators**: `auto` tries `kim` → `orb` → `nequix` → ASE **EMT** (Al/Cu/Ag/Au/Ni/Pd/Pt)
- **Optimization** and **single-point** energy/forces/stress
- **Molecular dynamics**: Velocity Verlet, Langevin, NVT Berendsen, **NPT Berendsen**
- **Recipe tool** `relax_and_md_workflow` (relax then MD)
- **Isotropic bulk modulus** from a 5-point energy-vs-strain fit
- **Analysis outputs**: RDF + coordination, MSD + thermo trends, VACF + diffusion
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

Without the extra, use `calculator_name='auto'`, `'emt'`, `'orb'`, or `'nequix'`. Runtime code already falls back when KIM is missing. EMT covers Al, Cu, Ag, Au, Ni, Pd, and Pt.

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

- `list_workspace_capabilities_workflow`
- `build_structure_workflow`
- `import_structure_workflow`
- `manipulate_structure_workflow`
- `analyze_structure_workflow`
- `write_structure_workflow`
- `optimize_structure_workflow`
- `single_point_workflow`
- `estimate_elastic_workflow`
- `run_md_workflow`
- `relax_and_md_workflow`
- `analyze_trajectory_workflow`
- `autocorrelation_workflow`

Legacy aliases are also registered: `build_structure`, `read_structure_file`, `write_structure_file`, `optimize_with_mlip`.

Call `list_workspace_capabilities_workflow` first from an agent. It reports which calculators imported, EMT element support, integrators, structure types, and edit operations.

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

Paste an existing geometry with `import_structure_workflow` (`xyz`, `cif`, or `poscar` text).

### Edits and defects

`manipulate_structure_workflow` operations:

- `rotate`, `translate`, `strain`, `supercell`, `wrap`
- `vacancy` (`operation_kwargs.index`)
- `substitute` (`index`, `symbol`)
- `interstitial` (`symbol`, optional `position`)

### Optimization options

`optimize_structure_workflow` exposes:

- `max_steps`, `fmax` (convergence)
- `maxstep`, `alpha` (BFGS step/damping controls)
- `constraints` (`fixed_atoms`, `fixed_bonds`, `fixed_cell`)

### Single-point and elasticity

`single_point_workflow` computes **energy**, **forces**, and **stress** (if periodic).

`estimate_elastic_workflow` fits E(strain) at five isotropic strains and returns `bulk_modulus_GPa` plus `calculator_used`.

### MD integrators / ensembles

`run_md_workflow` supports:

- `velocityverlet` / `nve` (NVE)
- `langevin` / `nvt-langevin` (NVT)
- `nvt` / `nvt-berendsen` (NVT)
- `npt` / `npt-berendsen` (NPT; `pressure_GPa`, `taup`)

`relax_and_md_workflow` chains optimization then MD.

Every energy/MD result includes `calculator_requested`, `calculator_used`, and `calculator_fallbacks` so an EMT copper run is not mistaken for an MLIP result.

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
  - `http_app.py` `TOOL_NAMES`
- Preserve `http_app.py` compatibility behavior unless intentionally changing deployment contracts.

---

## 📄 License

MIT — see `LICENSE`.
