"""Tests for the file-based catalog."""

import json
from pathlib import Path

import pytest

from mcp_atomictoolkit.catalog import (
    list_catalog_entries,
    register_catalog_entry,
    remove_catalog_entry,
)


@pytest.fixture
def catalog_path(tmp_path, monkeypatch):
    path = tmp_path / "catalog.json"
    monkeypatch.setenv("ATOMIC_TOOLKIT_CATALOG", str(path))
    return path


def test_register_and_list(catalog_path):
    result = register_catalog_entry(
        name="emt-cu",
        kind="potential",
        uri="builtin:emt",
        metadata={"elements": ["Cu"]},
    )
    assert result["action"] == "created"
    assert result["entry"]["name"] == "emt-cu"
    listed = list_catalog_entries()
    assert len(listed["entries"]) == 1
    assert listed["entries"][0]["uri"] == "builtin:emt"
    filtered = list_catalog_entries(kind="model")
    assert filtered["entries"] == []


def test_update_existing(catalog_path):
    register_catalog_entry(name="m1", kind="model", uri="hf://old")
    result = register_catalog_entry(name="m1", kind="model", uri="hf://new")
    assert result["action"] == "updated"
    assert result["entry"]["uri"] == "hf://new"
    assert len(list_catalog_entries()["entries"]) == 1


def test_remove(catalog_path):
    register_catalog_entry(name="d1", kind="dataset", uri="file:///tmp/data")
    removed = remove_catalog_entry("d1", "dataset")
    assert removed["removed"] == 1
    assert list_catalog_entries()["entries"] == []


def test_bad_kind(catalog_path):
    with pytest.raises(ValueError, match="kind"):
        register_catalog_entry(name="x", kind="unknown", uri="u")
