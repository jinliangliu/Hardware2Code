"""
Pydantic v2 type models for Hardware2Code YAML schema.

Replaces bare dictionaries with type-safe, validated models.
Provides automatic field validation, better error messages, and
self-documenting schema at the YAML input boundary.

Usage:
    hw = HardwareModel.model_validate(raw_yaml_dict)
    hw_dict = hw.model_dump()  # back to dict for template rendering
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PullMode(str, Enum):
    UP = "up"
    DOWN = "down"


class ExtiTrigger(str, Enum):
    RISING = "rising"
    FALLING = "falling"
    BOTH = "both"


class SleepMode(str, Enum):
    STOP0 = "STOP0"
    STOP1 = "STOP1"
    STOP2 = "STOP2"
    STANDBY = "STANDBY"
    SLEEP = "SLEEP"


# ---------------------------------------------------------------------------
# Pin models
# ---------------------------------------------------------------------------

class ExtiConfig(BaseModel):
    """EXTI (external interrupt) configuration for a pin."""
    model_config = ConfigDict(extra="allow")

    enable: bool = False
    trigger: Optional[ExtiTrigger] = None


class PinModel(BaseModel):
    """A single GPIO pin definition."""
    model_config = ConfigDict(extra="allow")

    id: str
    function: str
    label: Optional[str] = None
    pull: Optional[PullMode] = None
    active_level: Optional[Literal["high", "low"]] = None
    af: int = 0
    notify_task: str = ""
    exti: ExtiConfig = Field(default_factory=ExtiConfig)

    @field_validator("id")
    @classmethod
    def _validate_pin_id(cls, v: str) -> str:
        if not re.match(r"^P[A-F][0-9]{1,2}$", v):
            raise ValueError(
                f"Invalid pin ID '{v}'. Expected format like 'PA0' or 'PC13'."
            )
        return v


# ---------------------------------------------------------------------------
# MCU model
# ---------------------------------------------------------------------------

class McuModel(BaseModel):
    """MCU configuration section."""
    model_config = ConfigDict(extra="allow")

    part: str
    core_clock_mhz: int = 64
    hse_freq: int = 8000000

    @field_validator("part")
    @classmethod
    def _validate_part(cls, v: str) -> str:
        if not re.match(r"^STM32[A-Z0-9]+$", v):
            raise ValueError(
                f"Invalid MCU part number '{v}'. Expected format like 'STM32G0B1RET6'."
            )
        return v


# ---------------------------------------------------------------------------
# Task model
# ---------------------------------------------------------------------------

class TaskModel(BaseModel):
    """FreeRTOS task configuration."""
    model_config = ConfigDict(extra="allow")

    name: str
    priority: int = Field(ge=0, le=31)
    stack_size: int = Field(default=128, gt=0)


# ---------------------------------------------------------------------------
# Peripheral model
# ---------------------------------------------------------------------------

_VALID_PERIPHERAL_TYPES = frozenset({
    "Internal_RTC", "Internal_PWM", "Internal_ADC", "Internal_IR",
    "Internal_CLI", "Internal_IWDG",
    "UART_Serial",
    "I2C_Sensor_MPU6050", "I2C_EEPROM",
    "SPI_Flash_W25Q32", "SPI_Flash_Generic",
    "RS485", "Cellular_4G",
    "Protocol_Modbus", "Protocol_MQTT",
})


class PeripheralModel(BaseModel):
    """A single peripheral configuration."""
    model_config = ConfigDict(extra="allow")

    name: str
    type: str
    interface: Optional[str] = None
    bus: Optional[str] = None
    uart: Optional[str] = None
    bearer: Optional[str] = None
    broker: Optional[str] = None
    clock_source: Optional[str] = None
    features: list[str] = Field(default_factory=list)
    instance: Optional[str] = None
    extra: dict = Field(default_factory=dict)
    # Runtime field injected by detect_peripherals, not from YAML
    model: Optional[dict] = None

    @field_validator("type")
    @classmethod
    def _validate_type(cls, v: str) -> str:
        if v not in _VALID_PERIPHERAL_TYPES:
            raise ValueError(
                f"Unknown peripheral type '{v}'. "
                f"Valid types: {sorted(_VALID_PERIPHERAL_TYPES)}"
            )
        return v


# ---------------------------------------------------------------------------
# Sleep / Log / Bootloader / HIL configs
# ---------------------------------------------------------------------------

class SleepModel(BaseModel):
    """Low-power sleep configuration."""
    model_config = ConfigDict(extra="allow")

    mode: Optional[SleepMode] = None


class LogModel(BaseModel):
    """Logging subsystem configuration."""
    model_config = ConfigDict(extra="allow")

    enable: bool = False


class BootloaderModel(BaseModel):
    """Bootloader / dual-slot configuration."""
    model_config = ConfigDict(extra="allow")

    enabled: bool = False
    size_kb: int = Field(default=8, ge=4, le=32)
    app_a_offset: int = 0x2000
    app_b_offset: int = 0x40000
    crc_method: str = "crc32_hw"
    boot_flag_src: str = "tamp_bkp"
    max_retries: int = Field(default=3, ge=1, le=10)
    wdg_timeout_ms: int = 5000

    @model_validator(mode="after")
    def _validate_offsets(self) -> "BootloaderModel":
        if self.app_a_offset >= self.app_b_offset:
            raise ValueError(
                f"app_a_offset (0x{self.app_a_offset:X}) must be less than "
                f"app_b_offset (0x{self.app_b_offset:X})"
            )
        min_offset = self.size_kb * 1024
        if self.app_a_offset < min_offset:
            raise ValueError(
                f"app_a_offset (0x{self.app_a_offset:X}) must be >= "
                f"bootloader size ({self.size_kb}KB = 0x{min_offset:X})"
            )
        return self


class HilModel(BaseModel):
    """HIL (Hardware-In-Loop) test configuration."""
    model_config = ConfigDict(extra="allow")

    baudrate: int = 115200
    uart: str = "UART2"
    tx_pin: str = "PA2"
    rx_pin: str = "PA3"


# ---------------------------------------------------------------------------
# Business Flow models (state machine)
# ---------------------------------------------------------------------------

# Action can be a legacy string or a dict-format action
ActionType = Union[str, dict[str, Any]]


class VariableModel(BaseModel):
    """State machine variable declaration."""
    model_config = ConfigDict(extra="allow")

    name: str
    type: str
    initial: Any = None


class TransitionModel(BaseModel):
    """State transition definition."""
    model_config = ConfigDict(extra="allow")

    event: str
    target: Optional[str] = None
    guard: Optional[str] = None
    actions: list[ActionType] = Field(default_factory=list)


class StateModel(BaseModel):
    """State machine state (supports nesting and refs)."""
    model_config = ConfigDict(extra="allow")

    name: str
    type: Optional[Literal["ref"]] = None
    ref: Optional[str] = None
    namespace: Optional[str] = None
    after: Optional[int] = None
    history: bool = False
    initial_state: Optional[str] = None
    on_entry: list[ActionType] = Field(default_factory=list)
    on_exit: list[ActionType] = Field(default_factory=list)
    transitions: list[TransitionModel] = Field(default_factory=list)
    states: list["StateModel"] = Field(default_factory=list)
    variables: list[VariableModel] = Field(default_factory=list)


class RegionModel(BaseModel):
    """Parallel region within a state machine."""
    model_config = ConfigDict(extra="allow")

    name: str
    initial_state: str
    variables: list[VariableModel] = Field(default_factory=list)
    states: list[StateModel] = Field(default_factory=list)


class BusinessFlowModel(BaseModel):
    """Top-level business flow / state machine definition."""
    model_config = ConfigDict(extra="allow")

    initial_state: Optional[str] = None
    variables: list[VariableModel] = Field(default_factory=list)
    events: list[dict] = Field(default_factory=list)
    states: list[StateModel] = Field(default_factory=list)
    regions: list[RegionModel] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Top-level Hardware model
# ---------------------------------------------------------------------------

class HardwareModel(BaseModel):
    """
    Root model for a hardware YAML file.

    Validates all fields, pins, peripherals, bootloader config, etc.
    Call .model_dump() to get back a validated dict for template rendering.
    """
    model_config = ConfigDict(extra="allow")

    mcu: McuModel
    project: Optional[dict] = None
    pins: list[PinModel] = Field(default_factory=list)
    log: LogModel = Field(default_factory=LogModel)
    sleep: SleepModel = Field(default_factory=SleepModel)
    app_tasks: list[TaskModel] = Field(default_factory=list)
    peripherals: list[PeripheralModel] = Field(default_factory=list)
    business_flow: Optional[BusinessFlowModel] = None
    bootloader: Optional[BootloaderModel] = None
    hil: Optional[HilModel] = None
    heap_size: str = "0x200"
    stack_size: str = "0x400"

    @field_validator("pins")
    @classmethod
    def _validate_unique_pin_ids(cls, v: list[PinModel]) -> list[PinModel]:
        ids = [p.id for p in v]
        duplicates = sorted({pid for pid in ids if ids.count(pid) > 1})
        if duplicates:
            raise ValueError(f"Duplicate pin IDs found: {duplicates}")
        return v

    @model_validator(mode="after")
    def _validate_led_task_consistency(self) -> "HardwareModel":
        has_led = any(p.label == "LED" for p in self.pins)
        has_led_task = any(t.name == "led_task" for t in self.app_tasks)
        if has_led_task and not has_led:
            raise ValueError(
                "'led_task' defined in app_tasks but no pin labeled 'LED' found."
            )
        return self


# Resolve forward references for recursive StateModel
StateModel.model_rebuild()
