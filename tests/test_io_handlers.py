from pathlib import Path

import pytest
from ase import Atoms

from mcp_atomictoolkit import io_handlers


def test_read_structure_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        io_handlers.read_structure(tmp_path / "missing.xyz")


def test_write_and_read_structure_roundtrip_xyz(tmp_path: Path) -> None:
    atoms = Atoms("H2", positions=[[0, 0, 0], [0, 0, 0.74]])
    target = tmp_path / "mol.xyz"

    io_handlers.write_structure(atoms, target)
    loaded = io_handlers.read_structure(target)

    assert loaded.get_chemical_formula() == "H2"
    assert len(loaded) == 2


def test_read_structure_wraps_ase_errors(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    file_path = tmp_path / "a.xyz"
    file_path.write_text("invalid")

    def _boom(*_args, **_kwargs):
        raise RuntimeError("bad parse")

    monkeypatch.setattr(io_handlers, "read", _boom)

    with pytest.raises(ValueError, match="Failed to read file"):
        io_handlers.read_structure(file_path)


def test_get_supported_formats_contains_expected_keys() -> None:
    supported = io_handlers.get_supported_formats()
    assert "xyz" in supported
    assert "cif" in supported
