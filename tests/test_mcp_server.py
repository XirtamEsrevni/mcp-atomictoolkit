from mcp_atomictoolkit.mcp_server import _run_tool


def test_run_tool_returns_structured_error_payload() -> None:
    def _boom(**_kwargs):
        raise RuntimeError("Cannot create cubic cell for hcp structure")

    result = _run_tool(
        "build_structure_workflow",
        _boom,
        formula="Cu",
        crystal_system="hcp",
        builder_kwargs={"a": 2.556, "c": 4.174},
    )

    assert result["status"] == "error"
    assert result["tool_name"] == "build_structure_workflow"
    assert result["error"]["type"] == "RuntimeError"
    assert "Cannot create cubic cell" in result["error"]["message"]
    assert result["hints"]
    assert "cubic" in result["hints"][0]
    assert "Do not replace the workflow" in result["next_action"]
