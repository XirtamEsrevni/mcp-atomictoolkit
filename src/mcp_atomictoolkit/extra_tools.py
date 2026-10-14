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
from mcp_atomictoolkit.analysis.thermodynamics import trajectory_thermodynamics
from mcp_atomictoolkit.analysis.comparison import structure_rmsd
from mcp_atomictoolkit.analysis.lite_isf import lite_intermediate_scattering
from mcp_atomictoolkit.io_handlers import export_lammps_data
from mcp_atomictoolkit.workflows.batch import batch_single_point
from mcp_atomictoolkit.analysis.coordination import coordination_analysis
from mcp_atomictoolkit.workflows.constraints import apply_fixed_atoms
from mcp_atomictoolkit.workflows.substitute import substitute_atom
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

    @mcp.tool(task=TaskConfig(mode="optional"))
    async def surface_energy_workflow_tool(
        formula: str = "Cu",
        crystal_system: str = "fcc",
        lattice_constant: float = 3.6,
        miller: Optional[List[int]] = None,
        size: Optional[List[int]] = None,
        layers: int = 3,
        vacuum: float = 8.0,
        calculator_name: str = DEFAULT_CALCULATOR_NAME,
    ) -> Dict:
        """Compute a slab surface energy in J/m^2 from bulk and slab single points."""
        return run_tool(
            "surface_energy_workflow",
            surface_energy_workflow,
            formula=formula,
            crystal_system=crystal_system,
            lattice_constant=lattice_constant,
            miller=miller or [1, 1, 1],
            size=size or [2, 2, 1],
            layers=layers,
            vacuum=vacuum,
            calculator_name=calculator_name,
        )

    surface_energy_workflow_tool.__name__ = "surface_energy_workflow"

    @mcp.tool(task=TaskConfig(mode="optional"))
    async def submit_neb_job_tool(
        initial_filepath: str,
        final_filepath: str,
        n_images: int = 3,
        calculator_name: str = DEFAULT_CALCULATOR_NAME,
        fmax: float = 0.1,
        max_steps: int = 20,
        input_format: Optional[str] = None,
    ) -> Dict:
        """Start an ASE NEB hop in the background. Poll get_job. Disabled on Render."""
        return run_tool(
            "submit_neb_job",
            submit_neb_job,
            initial_filepath=initial_filepath,
            final_filepath=final_filepath,
            n_images=n_images,
            calculator_name=calculator_name,
            fmax=fmax,
            max_steps=max_steps,
            input_format=input_format,
        )

    submit_neb_job_tool.__name__ = "submit_neb_job"

    @mcp.tool(task=TaskConfig(mode="optional"))
    async def submit_phonon_job_tool(
        input_filepath: str,
        calculator_name: str = DEFAULT_CALCULATOR_NAME,
        supercell: Optional[List[int]] = None,
        delta: float = 0.01,
        kpts: Optional[List[int]] = None,
        npts: int = 50,
        input_format: Optional[str] = None,
    ) -> Dict:
        """Start a finite-displacement phonon DOS. Poll get_job. Disabled on Render."""
        return run_tool(
            "submit_phonon_job",
            submit_phonon_job,
            input_filepath=input_filepath,
            calculator_name=calculator_name,
            supercell=supercell or [1, 1, 1],
            delta=delta,
            kpts=kpts or [2, 2, 2],
            npts=npts,
            input_format=input_format,
        )

    submit_phonon_job_tool.__name__ = "submit_phonon_job"

    @mcp.tool(task=TaskConfig(mode="optional"))
    async def submit_phonon_bands_job_tool(
        input_filepath: str,
        calculator_name: str = DEFAULT_CALCULATOR_NAME,
        supercell: Optional[list] = None,
        delta: float = 0.01,
        npoints: int = 20,
        input_format: Optional[str] = None,
    ) -> Dict:
        """Start a phonon band-structure job along a high-symmetry path. Poll get_job. Disabled on Render."""
        return run_tool(
            "submit_phonon_bands_job",
            submit_phonon_bands_job,
            input_filepath=input_filepath,
            calculator_name=calculator_name,
            supercell=supercell,
            delta=delta,
            npoints=npoints,
            input_format=input_format,
        )

    submit_phonon_bands_job_tool.__name__ = "submit_phonon_bands_job"

    @mcp.tool(task=TaskConfig(mode="optional"))
    async def fit_lj_workflow(
        input_paths: list,
        reference_energies: list,
        output_path: str = "fitted_lj.json",
        name: str = "fitted_lj",
        input_format: Optional[str] = None,
    ) -> Dict:
        """Fit a Lennard-Jones potential to reference energies and register it."""
        return run_tool(
            "fit_lj_workflow",
            fit_lj_and_save,
            input_paths=input_paths,
            reference_energies=reference_energies,
            output_path=output_path,
            name=name,
            input_format=input_format,
        )

    fit_lj_workflow.__name__ = "fit_lj_workflow"

    @mcp.tool(task=TaskConfig(mode="optional"))
    async def fit_morse_workflow(
        input_paths: list,
        reference_energies: list,
        output_path: str = "fitted_morse.json",
        name: str = "fitted_morse",
        input_format: Optional[str] = None,
    ) -> Dict:
        """Fit a Morse potential to reference energies and register it. Fits Render."""
        return run_tool(
            "fit_morse_workflow",
            fit_morse_and_save,
            input_paths=input_paths,
            reference_energies=reference_energies,
            output_path=output_path,
            name=name,
            input_format=input_format,
        )

    fit_morse_workflow.__name__ = "fit_morse_workflow"

    @mcp.tool(task=TaskConfig(mode="optional"))
    async def trajectory_thermodynamics_workflow(
        input_filepath: str,
        input_format: Optional[str] = None,
        skip_frames: int = 0,
    ) -> Dict:
        """Average energy, forces, pressure, and temperature from a trajectory. Fits Render."""
        return run_tool(
            "trajectory_thermodynamics_workflow",
            trajectory_thermodynamics,
            input_filepath=input_filepath,
            input_format=input_format,
            skip_frames=skip_frames,
        )

    trajectory_thermodynamics_workflow.__name__ = "trajectory_thermodynamics_workflow"

    @mcp.tool(task=TaskConfig(mode="optional"))
    async def structure_rmsd_workflow(
        reference_filepath: str,
        target_filepath: str,
        reference_format: Optional[str] = None,
        target_format: Optional[str] = None,
        align: bool = True,
    ) -> Dict:
        """RMSD between two structures with optional Kabsch alignment. Fits Render."""
        return run_tool(
            "structure_rmsd_workflow",
            structure_rmsd,
            reference_filepath=reference_filepath,
            target_filepath=target_filepath,
            reference_format=reference_format,
            target_format=target_format,
            align=align,
        )

    structure_rmsd_workflow.__name__ = "structure_rmsd_workflow"

    @mcp.tool(task=TaskConfig(mode="optional"))
    async def lite_isf_workflow(
        input_filepath: str,
        q_magnitude: float = 2.0,
        dt_fs: float = 5.0,
        max_lag: int = 50,
        input_format: Optional[str] = None,
    ) -> Dict:
        """Lightweight intermediate scattering function. Pure numpy, fits Render."""
        return run_tool(
            "lite_isf_workflow",
            lite_intermediate_scattering,
            input_filepath=input_filepath,
            q_magnitude=q_magnitude,
            dt_fs=dt_fs,
            max_lag=max_lag,
            input_format=input_format,
        )

    lite_isf_workflow.__name__ = "lite_isf_workflow"

    @mcp.tool(task=TaskConfig(mode="optional"))
    async def export_lammps_data_workflow(
        input_filepath: str,
        output_path: str,
        atom_style: str = "atomic",
        input_format: Optional[str] = None,
    ) -> Dict:
        """Export a structure to a LAMMPS data file. Fits Render."""
        return run_tool(
            "export_lammps_data_workflow",
            export_lammps_data,
            input_filepath=input_filepath,
            output_path=output_path,
            atom_style=atom_style,
            input_format=input_format,
        )

    export_lammps_data_workflow.__name__ = "export_lammps_data_workflow"

    @mcp.tool(task=TaskConfig(mode="optional"))
    async def batch_single_point_workflow(
        input_paths: list,
        calculator_name: str = DEFAULT_CALCULATOR_NAME,
        input_format: Optional[str] = None,
        max_structures: int = 20,
    ) -> Dict:
        """Single-point energy for each structure in a list. Limited batch size for Render."""
        return run_tool(
            "batch_single_point_workflow",
            batch_single_point,
            input_paths=input_paths,
            calculator_name=calculator_name,
            input_format=input_format,
            max_structures=max_structures,
        )

    batch_single_point_workflow.__name__ = "batch_single_point_workflow"

    @mcp.tool(task=TaskConfig(mode="optional"))
    async def coordination_analysis_workflow(
        input_filepath: str,
        cutoff: float = 3.0,
        input_format: Optional[str] = None,
    ) -> Dict:
        """Per-atom and species-averaged coordination numbers. Fits Render."""
        return run_tool(
            "coordination_analysis_workflow",
            coordination_analysis,
            input_filepath=input_filepath,
            cutoff=cutoff,
            input_format=input_format,
        )

    coordination_analysis_workflow.__name__ = "coordination_analysis_workflow"

    @mcp.tool(task=TaskConfig(mode="optional"))
    async def apply_fixed_atoms_workflow(
        input_filepath: str,
        output_filepath: str,
        indices: list,
        input_format: Optional[str] = None,
        output_format: Optional[str] = None,
    ) -> Dict:
        """Write a structure with FixAtoms on the given indices. Fits Render."""
        return run_tool(
            "apply_fixed_atoms_workflow",
            apply_fixed_atoms,
            input_filepath=input_filepath,
            output_filepath=output_filepath,
            indices=indices,
            input_format=input_format,
            output_format=output_format,
        )

    apply_fixed_atoms_workflow.__name__ = "apply_fixed_atoms_workflow"

    @mcp.tool(task=TaskConfig(mode="optional"))
    async def substitute_atom_workflow(
        input_filepath: str,
        output_filepath: str,
        index: int,
        new_symbol: str,
        input_format: Optional[str] = None,
        output_format: Optional[str] = None,
    ) -> Dict:
        """Replace one atom with a new element. Fits Render."""
        return run_tool(
            "substitute_atom_workflow",
            substitute_atom,
            input_filepath=input_filepath,
            output_filepath=output_filepath,
            index=index,
            new_symbol=new_symbol,
            input_format=input_format,
            output_format=output_format,
        )

    substitute_atom_workflow.__name__ = "substitute_atom_workflow"








    @mcp.tool(task=TaskConfig(mode="optional"))
    async def submit_dynasor_job_tool(
        input_filepath: str,
        dt_fs: float = 5.0,
        q_max: float = 20.0,
        window_size: int = 100,
        window_step: Optional[int] = None,
        max_frames: Optional[int] = None,
        input_format: Optional[str] = None,
        calculate_currents: bool = False,
    ) -> Dict:
        """Start a Dynasor dynamical structure factor job. Requires dynasor. Poll get_job. Disabled on Render."""
        return run_tool(
            "submit_dynasor_job",
            submit_dynasor_job,
            input_filepath=input_filepath,
            dt_fs=dt_fs,
            q_max=q_max,
            window_size=window_size,
            window_step=window_step,
            max_frames=max_frames,
            input_format=input_format,
            calculate_currents=calculate_currents,
        )

    submit_dynasor_job_tool.__name__ = "submit_dynasor_job"

    @mcp.tool(task=TaskConfig(mode="optional"))
    async def list_catalog_entries_tool(kind: Optional[str] = None) -> Dict:
        """List model/dataset/potential catalog entries."""
        return run_tool("list_catalog_entries", list_catalog_entries, kind=kind)

    list_catalog_entries_tool.__name__ = "list_catalog_entries"

    @mcp.tool(task=TaskConfig(mode="optional"))
    async def register_catalog_entry_tool(
        name: str,
        kind: str,
        uri: str,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Register or update a catalog entry (kind: model, dataset, potential, calculator)."""
        return run_tool(
            "register_catalog_entry",
            register_catalog_entry,
            name=name,
            kind=kind,
            uri=uri,
            metadata=metadata,
        )

    register_catalog_entry_tool.__name__ = "register_catalog_entry"

    @mcp.tool(task=TaskConfig(mode="optional"))
    async def remove_catalog_entry_tool(name: str, kind: str) -> Dict:
        """Remove a catalog entry by name and kind."""
        return run_tool(
            "remove_catalog_entry",
            remove_catalog_entry,
            name=name,
            kind=kind,
        )

    remove_catalog_entry_tool.__name__ = "remove_catalog_entry"

    @mcp.tool(task=TaskConfig(mode="optional"))
    async def compute_elastic_tensor_workflow(
        input_filepath: str,
        calculator_name: str = DEFAULT_CALCULATOR_NAME,
        strain: float = 0.005,
        input_format: Optional[str] = None,
    ) -> Dict:
        """Compute the full Voigt elastic tensor (Cij) and derived moduli."""
        return run_tool(
            "compute_elastic_tensor_workflow",
            compute_elastic_tensor,
            input_filepath=input_filepath,
            calculator_name=calculator_name,
            strain=strain,
            input_format=input_format,
        )

    compute_elastic_tensor_workflow.__name__ = "compute_elastic_tensor_workflow"

    @mcp.tool(task=TaskConfig(mode="optional"))
    async def register_calculator_from_file_tool(
        name: str,
        source_path: str,
        factory_name: str = "get_calculator",
    ) -> Dict:
        """Register a user-supplied ASE calculator factory from a local .py file."""
        return run_tool(
            "register_calculator_from_file",
            register_calculator_from_file,
            name=name,
            source_path=source_path,
            factory_name=factory_name,
        )

    register_calculator_from_file_tool.__name__ = "register_calculator_from_file"

    @mcp.tool(task=TaskConfig(mode="optional"))
    async def list_registered_calculators_tool() -> Dict:
        """List calculators registered at runtime."""
        return {"registered": list_registered()}

    list_registered_calculators_tool.__name__ = "list_registered_calculators"



    _REGISTERED = True
