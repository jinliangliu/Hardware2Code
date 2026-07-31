"""
param.py - Runtime parameter schema for params.yaml.

Parameters are typed, bounded values that can be read/written at runtime
via shell CLI or other interfaces. Each parameter belongs to a component.

Example params.yaml:
  params:
    - name: led_brightness
      component: shell
      type: uint32
      default: 128
      min: 0
      max: 255
      readonly: false
      description: "LED PWM duty cycle (0-255)"
"""

from __future__ import annotations

from typing import Optional, Any
from pydantic import BaseModel, Field, model_validator

PARAM_TYPES = {"int32", "uint32", "float", "bool"}


class ParamConfig(BaseModel):
    """A single runtime parameter definition."""

    name: str = Field(..., description="Unique parameter name (snake_case)")
    component: str = Field(
        default="system",
        description="Owning component name",
    )
    type: str = Field(
        default="uint32",
        description="Parameter type: int32, uint32, float, bool",
    )
    default: Any = Field(
        default=0,
        description="Default value at startup",
    )
    min: Optional[float] = Field(
        default=None,
        description="Minimum allowed value (inclusive)",
    )
    max: Optional[float] = Field(
        default=None,
        description="Maximum allowed value (inclusive)",
    )
    readonly: bool = Field(
        default=False,
        description="If True, value cannot be modified at runtime",
    )
    persistent: bool = Field(
        default=False,
        description="If True, value survives power cycle (requires NVM)",
    )
    description: str = Field(
        default="",
        description="Human-readable parameter description",
    )

    @model_validator(mode="after")
    def validate_param(self) -> "ParamConfig":
        if self.type not in PARAM_TYPES:
            raise ValueError(
                f"Unknown param type '{self.type}'. Supported: {PARAM_TYPES}"
            )
        # Validate default within range
        if self.min is not None and self.default < self.min:
            raise ValueError(
                f"Param '{self.name}': default={self.default} < min={self.min}"
            )
        if self.max is not None and self.default > self.max:
            raise ValueError(
                f"Param '{self.name}': default={self.default} > max={self.max}"
            )
        return self


class ParamsModel(BaseModel):
    """Root model for params.yaml."""

    params: list[ParamConfig] = Field(
        default_factory=list,
        description="List of runtime parameters",
    )

    @model_validator(mode="after")
    def check_unique_names(self) -> "ParamsModel":
        names = [p.name for p in self.params]
        duplicates = {n for n in names if names.count(n) > 1}
        if duplicates:
            raise ValueError(f"Duplicate param names: {duplicates}")
        return self
