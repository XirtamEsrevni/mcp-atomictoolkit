"""Tests for LAMMPS data export."""

from pathlib import Path

from ase.build import bulk
from ase.io import write, read

from mcp_atomictoolkit.io_handlers import export_lammps_data


def test_export_lammps_data(tmp_path):
    atoms = bulk("Cu", "fcc", a=3.6, cubic=True)
    src = tmp_path / "cu.cif"
    write(src, atoms)
    out = tmp_path / "cu.data"
    result = export_lammps_data(str(src), str(out))
    assert Path(result["output_path"]).exists()
    assert result["n_atoms"] == len(atoms)
    # Round-trip
    loaded = read(out, format="lammps-data")
    assert len(loaded) == len(atoms)
