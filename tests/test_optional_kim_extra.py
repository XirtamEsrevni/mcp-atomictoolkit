from pathlib import Path

import tomllib


def _pyproject() -> dict:
    root = Path(__file__).resolve().parents[1]
    return tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))


def test_kim_bindings_are_optional_extras() -> None:
    project = _pyproject()["project"]
    core = project["dependencies"]
    extras = project["optional-dependencies"]["kim"]

    assert not any(dep.startswith("kimpy") for dep in core)
    assert not any(dep.startswith("kim-query") for dep in core)
    assert any(dep.startswith("kimpy") for dep in extras)
    assert any(dep.startswith("kim-query") for dep in extras)


def test_fastmcp_and_mcp_are_pinned_below_breaking_majors() -> None:
    core = _pyproject()["project"]["dependencies"]
    fastmcp = next(dep for dep in core if dep.startswith("fastmcp"))
    mcp = next(dep for dep in core if dep.startswith("mcp"))
    assert "<4" in fastmcp
    assert "<2" in mcp
