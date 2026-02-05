# Atomistic Toolkit MCP Server

> [!NOTE]
> This project is under active development. Not everything is working yet.

An MCP-compatible server providing atomistic simulation capabilities through ASE, pymatgen, and machine learning interatomic potentials (MLIPs).

## Features
### ASE Tools
- Structure creation and manipulation
- Geometry optimization
- File I/O operations (read/write structures)

### MLIP calculators
- Optimization and MD workflows now default to the Nequix calculator on CPU.
- The default model is the smallest/fastest option (`nequix-mp-1`) using the JAX backend.

Example (standalone ASE usage):
```python
from nequix.calculator import NequixCalculator

atoms = ...
atoms.calc = NequixCalculator("nequix-mp-1", backend="jax")
```
## Deploy to Render (Web Service)
Render can run the MCP server directly from this repository.

### Files used by Render
- `requirements.txt`: installs this repo and its dependencies.
- `main.py`: optional entrypoint that starts the MCP server with the correct host/port and MCP HTTP transport.
- `render.yaml`: provides a reproducible Render service definition.

### render.yaml
The repository includes the `render.yaml` below:
```yaml
services:
  - type: web
    name: mcp-atomictoolkit
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn mcp_atomictoolkit.http_app:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /healthz
    envVars:
      - key: PYTHON_VERSION
        value: "3.13"
```

### One-time setup
1. In Render, create a **New Web Service** and connect this GitHub repo.
2. Render will auto-detect `render.yaml`. If prompted, confirm the build and start commands.
3. Deploy. Render sets `$PORT` automatically and Uvicorn binds to `0.0.0.0:$PORT`.
   (`python main.py` is also valid because it reads `$PORT`, but the blueprint defaults to the Uvicorn
   module invocation.)

### If Render reports "No open ports detected"
Ensure the service is using the Render blueprint values so Uvicorn starts the HTTP server.
Set these in the Render UI if they were overridden:

- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn mcp_atomictoolkit.http_app:app --host 0.0.0.0 --port $PORT`
- **Health Check Path**: `/healthz`
- If logs include `ImportError: cannot import name 'SseServerTransport'`, deploy with updated code that uses `mcp.http_app(..., transport="sse")` and ensure `fastmcp>=2.14.5` is installed.


### Downloadable artifacts (structures, plots, tables)
All tools now return an `artifacts` list when output files are created (for example: `extxyz`, `traj`, `cif`, `png`, `svg`, `eps`, `csv`, `dat`). Each artifact includes a `download_url` that can be opened directly in Cursor/Claude clients without embedding binary data in chat context. For structure outputs (`xyz`, `extxyz`, `cif`, `vasp`, `poscar`), the server also emits a companion `html_preview` artifact that opens an interactive 3D browser view (3Dmol.js) of the structure.

- Default URL shape: `/artifacts/<artifact_id>/<filename>`
- Public absolute URLs: set `ARTIFACT_BASE_URL` (or `PUBLIC_BASE_URL`) to your Render URL, e.g. `https://<service>.onrender.com`
- Downloads are served with attachment headers from the MCP app itself.

### Server URL
Once running, the MCP endpoint will be:
```
https://<render-service-name>.onrender.com/
```

Legacy SSE path compatibility is also exposed at:
```
https://<render-service-name>.onrender.com/sse/
```

### Listing on Smithery
When you list the server on Smithery, use the root MCP URL (`https://<service>.onrender.com/`) as the server endpoint and
set the transport to **Streamable HTTP**. The `/sse/` path remains as a compatibility alias (`/sse` redirects to it).

### Troubleshooting: "Authorization Required" during scan
If Smithery (or another MCP directory/scanner) shows **"Authorization Required"** for your
Render deployment, it usually means the scanner is not reaching a publicly accessible MCP endpoint.

Checklist:

1. Use the public service URL (not a dashboard URL), for example:
   `https://<service-name>.onrender.com/`
2. In Render, verify the service is a **Web Service** and is publicly reachable.
3. Make sure no access control layer is enabled in front of the app (for example:
   Render-level protection, Cloudflare Access, OAuth proxy, or Basic Auth middleware).
4. Confirm your start command is exactly:
   `uvicorn mcp_atomictoolkit.http_app:app --host 0.0.0.0 --port $PORT`
5. Verify the app responds on Render:
   - `GET /healthz` should return HTTP 200.
   - `POST /` should not return `405` (this is the Streamable HTTP MCP endpoint).
6. Provide an MCP server card for auto-scanners:
   - `GET /.well-known/mcp/server-card.json` should return HTTP 200 JSON.
   - The server card should advertise your public root MCP URL (`/`).

Quick local check:
```bash
curl -i https://<service-name>.onrender.com/healthz
curl -i -X POST https://<service-name>.onrender.com/
curl -i https://<service-name>.onrender.com/.well-known/mcp/server-card.json
```

If `/sse` returns HTML for a login page or a `401/403`, the scanner will show
"Authorization Required" until that external auth layer is removed or configured for public access.
If scanner logs report `Initialization failed with status 404`, it often means the scanner tried
the wrong path and could not discover your MCP endpoint; serving a valid server card resolves this.
