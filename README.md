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
- **Optimization workflows** with MLIPs (`nequix` default, `orb` supported)
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

```bash
pip install -r requirements.txt
```

### 3) Run locally

```bash
uvicorn mcp_atomictoolkit.http_app:app --host 0.0.0.0 --port 10000
```

Alternative:

```bash
python main.py
```

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
- `run_md_workflow`
- `analyze_trajectory_workflow`
- `autocorrelation_workflow`

Legacy aliases are also included for backward compatibility.

---

## 🌐 Endpoints

- `POST /` — primary MCP Streamable HTTP endpoint
- `GET /healthz` — health check
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

## 📈 GitHub Pulse

> Add your repository path in the URLs below to enable live charts.

### Star history

[![Star History Chart](https://api.star-history.com/svg?repos=OWNER/REPO&type=Date)](https://star-history.com/#OWNER/REPO&Date)

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
