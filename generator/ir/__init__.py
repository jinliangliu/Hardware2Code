"""
ir - Intermediate Representation layer for the hw2c code generator.

Design principle: YAML -> Builder -> IR (typed dataclasses) -> Jinja2 (render-only).

The IR is a formal, typed data model that sits between the context builder
and the template engine. Templates receive IR objects and perform pure
rendering — no conditional logic, no computation.

All IR classes inherit from `IRObject` which provides `to_dict()` for
backward compatibility with the legacy flat-dict render path.
"""

from .project import ProjectIR
from .mcu import McuIR
from .pin import PinIR
from .peripheral import PeripheralIR, DriverIR
from .behavior import BehaviorIR
from .bootloader import BootIR
from .hil import HilIR
from .log import LogIR
from .exti import ExtiIR
from .rtc import RtcIR, RtcAlarmIR, RtcInitTimeIR
from .base import IRObject

__all__ = [
    "IRObject",
    "ProjectIR",
    "McuIR",
    "PinIR",
    "PeripheralIR",
    "DriverIR",
    "BehaviorIR",
    "BootIR",
    "HilIR",
    "LogIR",
    "ExtiIR",
    "RtcIR",
    "RtcAlarmIR",
    "RtcInitTimeIR",
]
