from pathlib import Path

import pytest

from mcp_atomictoolkit import artifact_store


def test_register_and_get_round_trip(tmp_path: Path) -> None:
    sample = tmp_path / "sample.txt"
    sample.write_text("data", encoding="utf-8")

    record = artifact_store.artifact_store.register(sample)
    fetched = artifact_store.artifact_store.get(record.artifact_id)

    assert record.artifact_id.startswith("art_")
    assert fetched == record
    assert record.filepath == sample.resolve()


def test_is_artifact_candidate_and_iter(tmp_path: Path) -> None:
    allowed = tmp_path / "file.txt"
    allowed.write_text("content", encoding="utf-8")
    blocked = tmp_path / "file.bin"
    blocked.write_bytes(b"binary")

    assert artifact_store._is_artifact_candidate(str(allowed))
    assert not artifact_store._is_artifact_candidate(str(blocked))

    nested = {"a": str(allowed), "b": {"c": str(blocked)}}
    found = list(artifact_store._iter_candidate_paths(nested))
    assert found == [("a", str(allowed))]


def test_with_downloadable_artifacts_adds_preview(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ARTIFACT_BASE_URL", "https://example.test")

    structure = tmp_path / "structure.xyz"
    structure.write_text("1\nComment\nH 0 0 0\n", encoding="utf-8")

    result = artifact_store.with_downloadable_artifacts({"structure": str(structure)})

    assert "artifacts" in result
    assert result["artifacts"][0]["download_url"].startswith("https://example.test/")
    assert any(item["artifact_type"] == "html_preview" for item in result["artifacts"])
    preview_path = Path(
        next(item["filepath"] for item in result["artifacts"] if item["artifact_type"] == "html_preview")
    )
    assert preview_path.exists()


def test_with_downloadable_artifacts_no_candidates() -> None:
    result = artifact_store.with_downloadable_artifacts({"value": "not-a-path"})
    assert result == {"value": "not-a-path"}


def test_request_base_url_context_override() -> None:
    token = artifact_store.set_request_base_url("https://example.test/base/")
    try:
        assert artifact_store._artifact_base_url() == "https://example.test/base"
    finally:
        artifact_store.reset_request_base_url(token)
