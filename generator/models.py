"""
models.py - Backward-compatibility re-export.

All Pydantic model definitions have moved to schemas/ package.
This module re-exports the public API so existing imports continue to work.
"""

from .schemas.hardware import (   # noqa: F401  — re-export for backward compat
    # Enums
    PullMode,
    ExtiTrigger,
    SleepMode,
    # Pin models
    ExtiConfig,
    PinConfig,
    PinModel,
    # MCU
    McuModel,
    # Task
    TaskModel,
    # Peripheral
    PeripheralModel,
    # Config sections
    SleepModel,
    LogModel,
    BootloaderModel,
    HilModel,
    # Business flow
    VariableModel,
    TransitionModel,
    StateModel,
    RegionModel,
    BusinessFlowModel,
    ActionType,
    # Root
    HardwareModel,
    # Constants
    VALID_PERIPHERAL_TYPES,
)
