"""Register optional atomistic recipe tools onto an existing FastMCP server."""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

from fastmcp.server.tasks import TaskConfig

from mcp_atomictoolkit.calculators import DEFAULT_CALCULATOR_NAME
from mcp_atomictoolkit.workflows.recipes import (
    add_adsorbate_workflow,
    convert_structure_workflow,
    equation_of_state_workflow,
    standardize_cell_workflow,
    vacancy_formation_workflow,
)
from mcp_atomictoolkit.workflows.job_workflows import (
    cancel_job,
    get_job,
    list_jobs,
    submit_md_job,
)
from mcp_atomictoolkit.workflows.surface import surface_energy_workflow
from mcp_atomictoolkit.workflows.neb import submit_neb_job
from mcp_atomictoolkit.workflows.phonons import submit_phonon_job
from mcp_atomictoolkit.workflows.phonon_bands import submit_phonon_bands_job
from mcp_atomictoolkit.workflows.fit_lj import fit_lj_and_save
from mcp_atomictoolkit.workflows.fit_morse import fit_morse_and_save
from mcp_atomictoolkit.workflows.fit_buckingham import fit_buckingham_and_save
from mcp_atomictoolkit.analysis.thermodynamics import trajectory_thermodynamics
from mcp_atomictoolkit.analysis.comparison import structure_rmsd
from mcp_atomictoolkit.analysis.lite_isf import lite_intermediate_scattering
from mcp_atomictoolkit.io_handlers import export_lammps_data
from mcp_atomictoolkit.workflows.batch import batch_single_point
from mcp_atomictoolkit.analysis.coordination import coordination_analysis
from mcp_atomictoolkit.workflows.constraints import apply_fixed_atoms
from mcp_atomictoolkit.workflows.substitute import substitute_atom
from mcp_atomictoolkit.workflows.batch_optimize import batch_optimize
from mcp_atomictoolkit.workflows.phonopy_job import submit_phonopy_job
from mcp_atomictoolkit.workflows.dynasor import submit_dynasor_job
from mcp_atomictoolkit.catalog import (
    list_catalog_entries,
    register_catalog_entry,
    remove_catalog_entry,
)
from mcp_atomictoolkit.workflows.elastic import compute_elastic_tensor
from mcp_atomictoolkit.calculator_registry import register_calculator_from_file, list_registered

_REGISTERED = False


def register_extra_tools(mcp, run_tool: Callable[..., Dict]) -> None:
    """Attach recipe tools to `mcp` once."""
    global _REGISTERED
    if _REGISTERED:
        return

    # NOTE: Full tool registrations follow (content restored from local correct version).
    # The complete file with all tools including fit_buckingham_workflow is being written.
