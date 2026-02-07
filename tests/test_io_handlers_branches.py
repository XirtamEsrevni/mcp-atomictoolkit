from pathlib import Path
import importlib
import sys
import types

import pytest


def _load_io_handlers(monkeypatch):
    ase_stub = types.ModuleType("ase")
    ase_io_stub = types.ModuleType("ase.io")
    ase_stub.Atoms = object
    ase_io_stub.read = lambda *args, **kwargs: None
    ase_io_stub.write = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, "ase", ase_stub)
    monkeypatch.setitem(sys.modules, "ase.io", ase_io_stub)
    sys.modules.pop("mcp_atomictoolkit.io_handlers", None)
    return importlib.import_module("mcp_atomictoolkit.io_handlers")


def test_read_structure_missing_file(monkeypatch, tmp_path: Path) -> None:
    io_handlers = _load_io_handlers(monkeypatch)
    with pytest.raises(FileNotFoundError):
        io_handlers.read_structure(tmp_path / "missing.xyz")


def test_read_structure_uses_extension(monkeypatch, tmp_path: Path) -> None:
    io_handlers = _load_io_handlers(monkeypatch)
    sample = tmp_path / "sample.xyz"
    sample.write_text("data", encoding="utf-8")

    captured = {}

    def fake_read(filepath, format=None):
        captured["filepath"] = filepath
        captured["format"] = format
        return "atoms"

    monkeypatch.setattr(io_handlers, "read", fake_read)

    atoms = io_handlers.read_structure(sample)

    assert atoms == "atoms"
    assert captured["format"] == "xyz"


def test_read_structure_raises_value_error(monkeypatch, tmp_path: Path) -> None:
    io_handlers = _load_io_handlers(monkeypatch)
    sample = tmp_path / "sample.xyz"
    sample.write_text("data", encoding="utf-8")

    def fake_read(filepath, format=None):
        raise RuntimeError("boom")

    monkeypatch.setattr(io_handlers, "read", fake_read)

    with pytest.raises(ValueError, match="Failed to read file"):
        io_handlers.read_structure(sample)


def test_write_structure_uses_extension(monkeypatch, tmp_path: Path) -> None:
    io_handlers = _load_io_handlers(monkeypatch)
    captured = {}

    def fake_write(filepath, atoms, format=None, **kwargs):
        captured["filepath"] = filepath
        captured["format"] = format
        captured["atoms"] = atoms
        captured["kwargs"] = kwargs

    monkeypatch.setattr(io_handlers, "write", fake_write)

    io_handlers.write_structure("atoms", tmp_path / "output.xyz")

    assert captured["format"] == "xyz"


def test_write_structure_raises_value_error(monkeypatch, tmp_path: Path) -> None:
    io_handlers = _load_io_handlers(monkeypatch)
    def fake_write(filepath, atoms, format=None, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(io_handlers, "write", fake_write)

    with pytest.raises(ValueError, match="Failed to write file"):
        io_handlers.write_structure("atoms", tmp_path / "output.xyz")
