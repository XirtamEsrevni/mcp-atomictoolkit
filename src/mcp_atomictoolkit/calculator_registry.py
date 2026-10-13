"""Runtime registry for user-supplied ASE calculator factories."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Callable, Dict, Optional

_REGISTRY: Dict[str, Callable] = {}


def register_calculator(name: str, factory: Callable) -> None:
    """Register a callable that returns an ASE calculator."""
    if not name or not name.strip():
        raise ValueError("name is required")
    if not callable(factory):
        raise ValueError("factory must be callable")
    _REGISTRY[name.strip().lower()] = factory


def unregister_calculator(name: str) -> bool:
    return _REGISTRY.pop(name.strip().lower(), None) is not None


def get_registered(name: str) -> Optional[Callable]:
    return _REGISTRY.get(name.strip().lower())


def list_registered() -> list[str]:
    return sorted(_REGISTRY)


def register_calculator_from_file(name: str, source_path: str, factory_name: str = "get_calculator") -> Dict:
    """Load a Python file and register the named factory.

    The file must define a callable `factory_name` that returns an ASE calculator.
    Only local paths are accepted (no URL fetching).
    """
    path = Path(source_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Calculator source not found: {path}")
    if path.suffix != ".py":
        raise ValueError("source_path must be a .py file")

    spec = importlib.util.spec_from_file_location(f"user_calc_{name}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    factory = getattr(module, factory_name, None)
    if not callable(factory):
        raise AttributeError(f"{path} does not define a callable '{factory_name}'")
    register_calculator(name, factory)
    return {"name": name.strip().lower(), "source": str(path), "factory": factory_name}
