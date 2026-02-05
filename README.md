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
- `main.py`: optional entrypoint that starts the MCP server with the correct host/port and SSE transport.
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

### If Render reports "No open ports detected"
Ensure the service is using the Render blueprint values so Uvicorn starts the HTTP server.
Set these in the Render UI if they were overridden:

- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn mcp_atomictoolkit.http_app:app --host 0.0.0.0 --port $PORT`
- **Health Check Path**: `/healthz`

### Server URL
Once running, the SSE endpoint will be:
```
https://<render-service-name>.onrender.com/sse
```

### Listing on Smithery
When you list the server on Smithery, use the SSE URL above as the server endpoint and
set the transport to SSE/HTTP as required by their listing form.
