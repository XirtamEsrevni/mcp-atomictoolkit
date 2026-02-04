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
