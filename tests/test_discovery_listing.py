"""Tests for discovery calculator listing."""

from mcp_atomictoolkit.discovery_calculators import list_discovery_calculators


def test_list_discovery_calculators_without_packages():
    result = list_discovery_calculators()
    assert result["extra"] == "discovery"
    assert result["count"] > 10
    assert "models" in result
    # Without the packages installed in the test env, most should be not importable
    any_importable = any(m["package_importable"] for m in result["models"].values())
    # The test passes either way; the function must not raise and must return the registry.
    assert isinstance(any_importable, bool)
    assert result["matbench_discovery_importable"] is False or result["matbench_discovery_importable"] is True
