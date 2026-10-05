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

_REGISTERED = False


def register_extra_tools(mcp, run_tool: Callable[..., Dict]) -> None:
    """Attach recipe tools to `mcp` once."""
    global _REGISTERED
    if _REGISTERED:
        return

    @mcp.tool(task=TaskConfig(mode="optional"))
    async def convert_structure_workflow_tool(
        input_filepath: str,
        output_filepath: str,
        input_format: Optional[str] = None,
        output_format: Optional[str] = None,
    ) -> Dict:
        """Convert a structure between xyz/cif/POSCAR/extxyz and other ASE formats."""
        return run_tool(
            "convert_structure_workflow",
            convert_structure_workflow,
            input_filepath=input_filepath,
            output_filepath=output_filepath,
            input_format=input_format,
            output_format=output_format,
        )

    convert_structure_workflow_tool.__name__ = "convert_structure_workflow"

    @mcp.tool(task=TaskConfig(mode="optional"))
    async def standardize_cell_workflow_tool(
        input_filepath: str,
        input_format: Optional[str] = None,
        output_filepath: str = "standardized.cif",
        output_format: Optional[str] = None,
        cell_type: str = "conventional",
        symprec: float = 0.1,
    ) -> Dict:
        """Rewrite a crystal to a primitive or conventional standard cell."""
        return run_tool(
            "standardize_cell_workflow",
            standardize_cell_workflow,
            input_filepath=input_filepath,
            input_format=input_format,
            output_filepath=output_filepath,
            output_format=output_format,
            cell_type=cell_type,
            symprec=symprec,
        )

    standardize_cell_workflow_tool.__name__ = "standardize_cell_workflow"

    @mcp.tool(task=TaskConfig(mode="optional"))
    async def equation_of_state_workflow_tool(
        input_filepath: str,
        input_format: Optional[str] = None,
        calculator_name: str = DEFAULT_CALCULATOR_NAME,
        strain_max: float = 0.06,
        n_points: int = 5,
        eos_type: str = "birchmurnaghan",
        plot_filepath: str = "eos.png",
    ) -> Dict:
        """Fit an equation of state and return V0, E0, and bulk modulus."""
        return run_tool(
            "equation_of_state_workflow",
            equation_of_state_workflow,
            input_filepath=input_filepath,
            input_format=input_format,
            calculator_name=calculator_name,
            strain_max=strain_max,
            n_points=n_points,
            eos_type=eos_type,
            plot_filepath=plot_filepath,
        )

    equation_of_state_workflow_tool.__name__ = "equation_of_state_workflow"

    @mcp.tool(task=TaskConfig(mode="optional"))
    async def vacancy_formation_workflow_tool(
        input_filepath: str,
        input_format: Optional[str] = None,
        calculator_name: str = DEFAULT_CALCULATOR_NAME,
        index: int = 0,
        vacancy_filepath: str = "vacancy.extxyz",
    ) -> Dict:
        """Estimate unrelaxed vacancy formation energy."""
        return run_tool(
            "vacancy_formation_workflow",
            vacancy_formation_workflow,
            input_filepath=input_filepath,
            input_format=input_format,
            calculator_name=calculator_name,
            index=index,
            vacancy_filepath=vacancy_filepath,
        )

    vacancy_formation_workflow_tool.__name__ = "vacancy_formation_workflow"

    @mcp.tool(task=TaskConfig(mode="optional"))
    async def add_adsorbate_workflow_tool(
        input_filepath: str,
        adsorbate: str,
        input_format: Optional[str] = None,
        output_filepath: str = "adsorbed.extxyz",
        height: float = 1.8,
        position: str = "ontop",
        make_slab: bool = False,
        miller_indices: Optional[List[int]] = None,
        layers: int = 3,
        vacuum: float = 10.0,
    ) -> Dict:
        """Add an adsorbate onto a surface (optionally cut a slab first)."""
        return run_tool(
            "add_adsorbate_workflow",
            add_adsorbate_workflow,
            input_filepath=input_filepath,
            adsorbate=adsorbate,
            input_format=input_format,
            output_filepath=output_filepath,
            height=height,
            position=position,
            make_slab=make_slab,
            miller_indices=miller_indices or [1, 1, 1],
            layers=layers,
            vacuum=vacuum,
        )

    add_adsorbate_workflow_tool.__name__ = "add_adsorbate_workflow"

    @mcp.tool(task=TaskConfig(mode="optional"))
    async def submit_md_job_tool(
        input_filepath: str,
        input_format: Optional[str] = None,
        output_trajectory_filepath: str = "md.extxyz",
        calculator_name: str = DEFAULT_CALCULATOR_NAME,
        integrator: str = "nvt",
        timestep_fs: float = 1.0,
        temperature_K: float = 300.0,
        steps: Optional[int] = None,
        duration_ps: Optional[float] = None,
        trajectory_interval: int = 10,
        pressure_GPa: float = 0.0,
    ) -> Dict:
        """Start MD in the background. Returns job_id immediately. 100 ps at 1 fs is 100000 steps. Poll get_job."""
        return run_tool(
            "submit_md_job",
            submit_md_job,
            input_filepath=input_filepath,
            input_format=input_format,
            output_trajectory_filepath=output_trajectory_filepath,
            calculator_name=calculator_name,
            integrator=integrator,
            timestep_fs=timestep_fs,
            temperature_K=temperature_K,
            steps=steps,
            duration_ps=duration_ps,
            trajectory_interval=trajectory_interval,
            pressure_GPa=pressure_GPa,
        )

    submit_md_job_tool.__name__ = "submit_md_job"

    @mcp.tool(task=TaskConfig(mode="optional"))
    async def get_job_tool(job_id: str) -> Dict:
        """Reconnect to a background job. Works from a new MCP session while the server process is alive."""
        return run_tool("get_job", get_job, job_id=job_id)

    get_job_tool.__name__ = "get_job"

    @mcp.tool(task=TaskConfig(mode="optional"))
    async def list_jobs_tool(limit: int = 20) -> Dict:
        """List background jobs on this server process."""
        return run_tool("list_jobs", list_jobs, limit=limit)

    list_jobs_tool.__name__ = "list_jobs"

    @mcp.tool(task=TaskConfig(mode="optional"))
    async def cancel_job_tool(job_id: str) -> Dict:
        """Ask a background job to stop between MD chunks."""
        return run_tool("cancel_job", cancel_job, job_id=job_id)

    cancel_job_tool.__name__ = "cancel_job"
    _REGISTERED = True
