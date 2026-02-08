"""Molecular dynamics runner utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from ase import Atoms, units
from ase.io import Trajectory, write
from ase.md.langevin import Langevin
from ase.md.nvtberendsen import NVTBerendsen
from ase.md.velocitydistribution import (
    MaxwellBoltzmannDistribution,
    Stationary,
    ZeroRotation,
)
from ase.md.verlet import VelocityVerlet
from ase.md.logger import MDLogger

from mcp_atomictoolkit.io_handlers import read_structure
from mcp_atomictoolkit.calculators import DEFAULT_CALCULATOR_NAME, resolve_calculator


@dataclass
class MDSummary:
    """Summary statistics for an MD run."""

    steps: int
    timestep_fs: float
    integrator: str
    target_temperature_K: float
    mean_temperature_K: float
    final_temperature_K: float
    initial_potential_energy: float
    final_potential_energy: float
    initial_kinetic_energy: float
    final_kinetic_energy: float
    initial_total_energy: float
    final_total_energy: float

    def as_dict(self) -> Dict[str, float]:
        """Convert summary to a dictionary."""
        return {
            "steps": self.steps,
            "timestep_fs": self.timestep_fs,
            "integrator": self.integrator,
            "target_temperature_K": self.target_temperature_K,
            "mean_temperature_K": self.mean_temperature_K,
            "final_temperature_K": self.final_temperature_K,
            "initial_potential_energy": self.initial_potential_energy,
            "final_potential_energy": self.final_potential_energy,
            "initial_kinetic_energy": self.initial_kinetic_energy,
            "final_kinetic_energy": self.final_kinetic_energy,
            "initial_total_energy": self.initial_total_energy,
            "final_total_energy": self.final_total_energy,
        }


def _attach_trajectory_writer(
    md,
    atoms: Atoms,
    trajectory_path: Path,
    fmt: str,
    interval: int,
) -> None:
    """Attach a trajectory writer to the MD run."""
    if fmt == "traj":
        traj = Trajectory(str(trajectory_path), "w", atoms)
        md.attach(traj.write, interval=interval)
        return

    if trajectory_path.exists():
        trajectory_path.unlink()

    def _write_extxyz():
        write(str(trajectory_path), atoms, format=fmt, append=True)

    md.attach(_write_extxyz, interval=interval)


def _initialize_velocities(atoms: Atoms, temperature_K: float) -> None:
    """Initialize velocities using a Maxwell-Boltzmann distribution."""
    MaxwellBoltzmannDistribution(atoms, temperature_K=temperature_K)
    Stationary(atoms)
    ZeroRotation(atoms)


def _select_integrator(
    atoms: Atoms,
    integrator: str,
    timestep_fs: float,
    temperature_K: float,
    friction: float,
    taut: float,
):
    """Return an ASE MD integrator."""
    integrator_lower = integrator.lower()
    dt = timestep_fs * units.fs
    if integrator_lower in {"velocityverlet", "nve"}:
        return VelocityVerlet(atoms, dt)
    if integrator_lower in {"langevin", "nvt-langevin"}:
        return Langevin(atoms, dt, temperature_K=temperature_K, friction=friction)
    if integrator_lower in {"nvt", "nvt-berendsen"}:
        return NVTBerendsen(atoms, dt, temperature_K=temperature_K, taut=taut)

    raise ValueError(
        "Unknown integrator. Use 'velocityverlet', 'langevin', or 'nvt'."
    )


def run_md(
    input_filepath: str,
    input_format: Optional[str] = None,
    output_trajectory_filepath: str = "md.extxyz",
    output_format: Optional[str] = None,
    log_filepath: str = "md.log",
    summary_filepath: str = "md_summary.txt",
    calculator_name: str = DEFAULT_CALCULATOR_NAME,
    integrator: str = "velocityverlet",
    timestep_fs: float = 1.0,
    temperature_K: float = 300.0,
    steps: int = 100,
    friction: float = 0.02,
    taut: float = 100.0,
    trajectory_interval: int = 1,
) -> Dict:
    """Run an ASE molecular dynamics simulation.

    Args:
        input_filepath: Path to input structure file.
        input_format: Structure file format (optional).
        output_trajectory_filepath: Path to output trajectory file (.traj/.extxyz).
        output_format: Trajectory format (optional, inferred from path).
        log_filepath: Path to log file for MD energies/temperature.
        summary_filepath: Path to summary file for MD statistics.
        calculator_name: Type of MLIP ('auto', 'kim', 'nequix', or 'orb'). Defaults to auto.
        integrator: Integrator ('velocityverlet', 'langevin', 'nvt').
        timestep_fs: MD timestep in femtoseconds.
        temperature_K: Target temperature in Kelvin.
        steps: Number of MD steps.
        friction: Langevin friction coefficient (1/fs).
        taut: NVT Berendsen thermostat time constant (fs).
        trajectory_interval: Interval between trajectory writes.

    Returns:
        Dict containing output file paths and summary statistics.
    """
    atoms = read_structure(input_filepath, input_format)
    species = sorted(set(atoms.get_chemical_symbols()))
    calculator, calculator_used, calculator_errors = resolve_calculator(
        calculator_name,
        species=species,
    )
    atoms.calc = calculator

    _initialize_velocities(atoms, temperature_K)

    md = _select_integrator(
        atoms=atoms,
        integrator=integrator,
        timestep_fs=timestep_fs,
        temperature_K=temperature_K,
        friction=friction,
        taut=taut,
    )

    trajectory_path = Path(output_trajectory_filepath)
    trajectory_path.parent.mkdir(parents=True, exist_ok=True)
    fmt = output_format or trajectory_path.suffix.lstrip(".") or "extxyz"
    _attach_trajectory_writer(
        md,
        atoms,
        trajectory_path,
        fmt,
        trajectory_interval,
    )

    log_path = Path(log_filepath)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = MDLogger(
        md,
        atoms,
        str(log_path),
        header=True,
        stress=False,
        peratom=False,
        mode="w",
    )
    md.attach(logger, interval=1)

    initial_potential = atoms.get_potential_energy()
    initial_kinetic = atoms.get_kinetic_energy()
    initial_total = initial_potential + initial_kinetic

    temperatures = []

    def _record_temperature():
        temperatures.append(atoms.get_temperature())

    md.attach(_record_temperature, interval=1)
    md.run(steps)

    final_potential = atoms.get_potential_energy()
    final_kinetic = atoms.get_kinetic_energy()
    final_total = final_potential + final_kinetic
    final_temperature = atoms.get_temperature()
    mean_temperature = (
        sum(temperatures) / len(temperatures) if temperatures else final_temperature
    )

    summary = MDSummary(
        steps=steps,
        timestep_fs=timestep_fs,
        integrator=integrator,
        target_temperature_K=temperature_K,
        mean_temperature_K=mean_temperature,
        final_temperature_K=final_temperature,
        initial_potential_energy=initial_potential,
        final_potential_energy=final_potential,
        initial_kinetic_energy=initial_kinetic,
        final_kinetic_energy=final_kinetic,
        initial_total_energy=initial_total,
        final_total_energy=final_total,
    )

    summary_path = Path(summary_filepath)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_text = "\n".join(
        f"{key}: {value}" for key, value in summary.as_dict().items()
    )
    summary_path.write_text(summary_text)

    return {
        "trajectory_filepath": str(trajectory_path.absolute()),
        "log_filepath": str(log_path.absolute()),
        "summary_filepath": str(summary_path.absolute()),
        "summary": summary.as_dict(),
        "calculator_requested": calculator_name,
        "calculator_used": calculator_used,
        "calculator_fallbacks": calculator_errors,
    }
