from ase.md.langevin import Langevin
from ase.md.nptberendsen import NPTBerendsen
from ase.md.nvtberendsen import NVTBerendsen
from ase.md.verlet import VelocityVerlet
from ase.build import bulk
import pytest

from mcp_atomictoolkit.md_runner import _select_integrator


def _cu_cell():
    return bulk("Cu", "fcc", a=3.6, cubic=True)


def test_select_integrator_nve_langevin_nvt_npt() -> None:
    atoms = _cu_cell()
    nve = _select_integrator(atoms, "nve", 1.0, 300.0, 0.02, 100.0)
    langevin = _select_integrator(atoms, "langevin", 1.0, 300.0, 0.02, 100.0)
    nvt = _select_integrator(atoms, "nvt-berendsen", 1.0, 300.0, 0.02, 100.0)
    npt = _select_integrator(
        atoms,
        "npt",
        1.0,
        300.0,
        0.02,
        100.0,
        pressure_GPa=0.1,
        taup=500.0,
    )

    assert isinstance(nve, VelocityVerlet)
    assert isinstance(langevin, Langevin)
    assert isinstance(nvt, NVTBerendsen)
    assert isinstance(npt, NPTBerendsen)


def test_select_integrator_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="Unknown integrator"):
        _select_integrator(_cu_cell(), "bad-ensemble", 1.0, 300.0, 0.02, 100.0)
