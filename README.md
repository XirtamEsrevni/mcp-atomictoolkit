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
## Deploy to Hugging Face (Docker Space)
Use a Docker Space to host the MCP server with SSE transport.

1. Create a new Hugging Face Space and select **Docker** as the SDK.
2. Push this repository to the Space.
3. Ensure the Space is running; it will start the MCP server on port `7860`.

### Files used by the Space
- `Dockerfile`: installs the package and runs the SSE server.
- `requirements.txt`: installs this repo and its dependencies.
- `hf_server.py`: starts the MCP server with the correct transport.

### Server URL
Once the Space is running, the SSE endpoint will be:
```
https://<hf-username>-<space-name>.hf.space/sse
```

### Listing on Smithery
When you list the server on Smithery, use the SSE URL above as the server endpoint and
set the transport to SSE/HTTP as required by their listing form.
