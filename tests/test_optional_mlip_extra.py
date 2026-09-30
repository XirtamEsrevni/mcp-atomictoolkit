from pathlib import Path

import tomllib


def test_orb_and_nequix_are_not_core_dependencies() -> None:
    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    core = project["dependencies"]
    mlip = project["optional-dependencies"]["mlip"]
    assert not any("orb-models" in dep for dep in core)
    assert not any(dep.startswith("nequix") for dep in core)
    assert any("orb-models" in dep for dep in mlip)
    assert any(dep.startswith("nequix") for dep in mlip)
