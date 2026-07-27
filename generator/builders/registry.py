"""
registry.py - Peripheral builder registry with decorator-based registration.

Usage:
    @register_builder("GPIO")
    class GpioBuilder(PeripheralBuilder):
        ...

    builder_cls = get_builder(peripheral)   # returns class or None
    all_builders = get_all_builders()       # returns list of classes

Adding a new peripheral type:
  1. Create builders/my_type_builder.py
  2. Decorate with @register_builder("MyType")
  3. Import the module in builders/__init__.py (to trigger registration)
"""

from __future__ import annotations

import importlib
import logging
import os
from typing import Callable, Optional, Type

from .base import PeripheralBuilder

logger = logging.getLogger("hw2c.registry")

# Global registry: peripheral_type -> Builder subclass
_registry: dict[str, Type[PeripheralBuilder]] = {}
_pending_auto_import: bool = True


def register_builder(peripheral_type: str) -> Callable:
    """Class decorator: register a PeripheralBuilder subclass.

    Args:
        peripheral_type: The type string this builder handles (e.g. "GPIO").
    """

    def decorator(cls: Type[PeripheralBuilder]) -> Type[PeripheralBuilder]:
        cls.peripheral_type = peripheral_type
        _registry[peripheral_type] = cls
        logger.debug(f"Registered builder '{peripheral_type}' -> {cls.__name__}")
        return cls

    return decorator


def get_builder(peripheral: dict) -> Optional[Type[PeripheralBuilder]]:
    """Get the registered builder class for a peripheral dict.

    Returns None if no builder is registered for this type.
    """
    _auto_import_builders()
    ptype = peripheral.get("type", "")
    return _registry.get(ptype)


def get_all_builders() -> list[Type[PeripheralBuilder]]:
    """Return all registered builder classes."""
    _auto_import_builders()
    return list(_registry.values())


def _auto_import_builders() -> None:
    """Import all builder modules to trigger @register_builder decorators.

    Only runs once (lazy).  Scans the builders/ directory for *_builder.py
    modules and imports them.
    """
    global _pending_auto_import
    if not _pending_auto_import:
        return
    _pending_auto_import = False

    builders_dir = os.path.dirname(os.path.abspath(__file__))
    for fname in os.listdir(builders_dir):
        if fname.endswith("_builder.py") and fname != "base.py":
            mod_name = f"builders.{fname[:-3]}"
            try:
                importlib.import_module(mod_name)
            except ImportError as e:
                logger.debug(f"Could not import {mod_name}: {e}")
