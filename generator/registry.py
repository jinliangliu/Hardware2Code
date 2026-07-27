"""
Backend registry - discovers and loads MCU target backends.

Backends can be registered via:
  1. Built-in default (STM32).
  2. Python entry_points 'hardware2code.backends' in installed packages.

Usage:
    backend = load_backend("stm32")
    backend = load_backend("nxp")  # requires hardware2code-nxp package
"""

import importlib.metadata
import logging
import sys
from typing import Dict, Optional

from .backends.base import TargetBackend

logger = logging.getLogger("hw2c.registry")

# Cache of loaded backends to avoid re-discovery
_loaded_backends: Dict[str, TargetBackend] = {}


def _discover_entry_points() -> Dict[str, type]:
    """Discover backends registered via entry_points.

    Returns:
        dict mapping backend name -> backend class.
    """
    backends: Dict[str, type] = {}
    try:
        entry_points = importlib.metadata.entry_points(
            group="hardware2code.backends"
        )
        for ep in entry_points:
            try:
                cls = ep.load()
                backends[ep.name] = cls
                logger.debug(f"Discovered backend '{ep.name}' from {ep.value}")
            except Exception as e:
                logger.warning(f"Failed to load backend '{ep.name}': {e}")
    except Exception as e:
        logger.debug(f"Entry point discovery skipped: {e}")

    return backends


def _get_builtin_backends() -> Dict[str, type]:
    """Return built-in backends that ship with hardware2code."""
    from .backends.stm32.backend import STM32Backend
    return {"stm32": STM32Backend}


def load_backend(name: str) -> TargetBackend:
    """Load and instantiate a backend by name.

    Backend resolution order:
      1. Cached instance
      2. Entry-point discovery (external packages)
      3. Built-in fallbacks (STM32)

    Args:
        name: Backend name (e.g., 'stm32').

    Returns:
        Instantiated TargetBackend.

    Raises:
        ValueError: If no backend matches the given name.
    """
    name = name.lower().strip()

    # Check cache
    if name in _loaded_backends:
        return _loaded_backends[name]

    # Discover available backends
    available = {}
    available.update(_get_builtin_backends())
    available.update(_discover_entry_points())

    if name not in available:
        raise ValueError(
            f"Backend '{name}' not found. "
            f"Available: {', '.join(sorted(available.keys()))}. "
            f"If '{name}' is a third-party backend, "
            f"try: pip install hardware2code-{name}"
        )

    cls = available[name]
    instance = cls()
    _loaded_backends[name] = instance
    logger.info(f"Loaded backend: {name} ({instance.get_mcu_family()})")
    return instance


def list_backends() -> Dict[str, str]:
    """List all available backends with their MCU families.

    Returns:
        dict mapping backend name -> MCU family string.
    """
    available = {}
    available.update(_get_builtin_backends())
    available.update(_discover_entry_points())

    result = {}
    for name, cls in available.items():
        try:
            result[name] = cls().get_mcu_family()
        except Exception:
            result[name] = "unknown"

    return result


def get_default_backend() -> TargetBackend:
    """Return the default backend (STM32)."""
    return load_backend("stm32")
