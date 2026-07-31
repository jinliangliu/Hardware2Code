"""
peripheral.py - Peripheral and Driver IR objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import IRObject


@dataclass
class PeripheralIR(IRObject):
    """Single peripheral instance from YAML."""

    name: str = ""
    type: str = ""
    model: dict = field(default_factory=dict)
    bus: str = ""
    uart: str = ""
    bearer: str = ""
    broker: str = ""
    extra: dict = field(default_factory=dict)
    # Pre-computed fields injected by builders
    _clock_source: str = ""
    _mpu6050: dict = field(default_factory=dict)


@dataclass
class DriverIR(IRObject):
    """Driver entry — maps a peripheral to its Jinja2 templates."""

    name: str = ""
    template: str = ""
    header_template: str = ""
    model: dict = field(default_factory=dict)
    peripheral: dict = field(default_factory=dict)
