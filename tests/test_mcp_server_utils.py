import importlib
import sys
import types

import pytest


def _load_mcp_server(monkeypatch):
    fastmcp_stub = types.ModuleType("fastmcp")

    class FakeFastMCP:
        def __init__(self, name: str):
            self.name = name

        def tool(self):
            def decorator(func):
                return func

            return decorator

        def http_app(self, **kwargs):
            async def app(scope, receive, send):
                return None

            return app

    fastmcp_stub.FastMCP = FakeFastMCP
    monkeypatch.setitem(sys.modules, "fastmcp", fastmcp_stub)

    workflows_stub = types.ModuleType("mcp_atomictoolkit.workflows.core")
    for name in (
        "analyze_structure_workflow",
        "analyze_trajectory_workflow",
        "autocorrelation_workflow",
        "build_structure_workflow",
        "optimize_structure_workflow",
        "run_md_workflow",
        "write_structure_workflow",
    ):
        setattr(
            workflows_stub,
            name,
            lambda _name=name, **kwargs: {"status": "ok", "name": _name},
        )
    monkeypatch.setitem(sys.modules, "mcp_atomictoolkit.workflows.core", workflows_stub)

    sys.modules.pop("mcp_atomictoolkit.mcp_server", None)
    return importlib.import_module("mcp_atomictoolkit.mcp_server")


def test_compact_kwargs_truncates(monkeypatch):
    mcp_server = _load_mcp_server(monkeypatch)
    data = {
        "long_str": "a" * 201,
        "long_list": list(range(26)),
        "long_dict": {str(i): i for i in range(26)},
        "short": "ok",
    }
    compacted = mcp_server._compact_kwargs(data)
    assert compacted["long_str"] == "<str:201 chars>"
    assert compacted["long_list"] == "<list:26 items>"
    assert compacted["long_dict"] == "<dict:26 keys>"
    assert compacted["short"] == "ok"


def test_error_hints_for_hcp(monkeypatch):
    mcp_server = _load_mcp_server(monkeypatch)
    hints = mcp_server._error_hints(
        "build_structure_workflow",
        {"crystal_system": "hcp", "builder_kwargs": {}},
        ValueError("Cubic lattice mismatch"),
    )
    assert any("hcp is not a cubic lattice" in hint for hint in hints)


def test_tool_error_response_includes_hints(monkeypatch):
    mcp_server = _load_mcp_server(monkeypatch)
    response = mcp_server._tool_error_response(
        "run_md_workflow",
        FileNotFoundError("file not found"),
        12.3,
        {"input_filepath": "missing.xyz"},
    )
    assert response["status"] == "error"
    assert response["tool_name"] == "run_md_workflow"
    assert response["error"]["type"] == "FileNotFoundError"
    assert any("Verify file paths" in hint for hint in response["hints"])
    assert any("Use returned artifact download_url links" in hint for hint in response["hints"])


def test_run_tool_success_and_failure(monkeypatch):
    mcp_server = _load_mcp_server(monkeypatch)

    def ok_tool():
        return {"status": "ok"}

    def bad_tool():
        raise RuntimeError("boom")

    ok_result = mcp_server._run_tool("ok_tool", ok_tool)
    assert ok_result["status"] == "ok"

    bad_result = mcp_server._run_tool("bad_tool", bad_tool)
    assert bad_result["status"] == "error"
    assert bad_result["tool_name"] == "bad_tool"
