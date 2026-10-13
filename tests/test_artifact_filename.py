from mcp_atomictoolkit.artifact_store import _is_artifact_candidate, with_downloadable_artifacts


def test_long_error_message_is_not_a_path():
    message = "Failed to initialize any MLIP calculator. " + ("Details: " * 40)
    assert len(message) > 255
    assert _is_artifact_candidate(message) is False
    result = with_downloadable_artifacts({"status": "error", "error": {"message": message}})
    assert result["error"]["message"] == message
