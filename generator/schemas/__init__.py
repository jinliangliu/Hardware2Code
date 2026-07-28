"""
generator.schemas - Pydantic v2 type models for Hardware2Code YAML schema.

All YAML configuration is validated through these models before reaching
the template rendering pipeline.  This package is the single source of
truth for the DSL schema.
"""

from .hardware import (
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
    # Business flow (state machine)
    VariableModel,
    TransitionModel,
    StateModel,
    RegionModel,
    BehaviorModel,
    # Root
    HardwareModel,
    # Types
    ActionType,
    # Constants
    VALID_PERIPHERAL_TYPES,
    VALID_PIN_FUNCTIONS,
    VALID_FUNCTION_PATTERNS,
)

__all__ = [
    "PullMode", "ExtiTrigger", "SleepMode",
    "ExtiConfig", "PinConfig", "PinModel",
    "McuModel", "TaskModel", "PeripheralModel",
    "SleepModel", "LogModel", "BootloaderModel", "HilModel",
    "VariableModel", "TransitionModel", "StateModel",
    "RegionModel", "BehaviorModel",
    "HardwareModel", "ActionType",
    "VALID_PERIPHERAL_TYPES", "VALID_PIN_FUNCTIONS",
    "VALID_FUNCTION_PATTERNS",
]
