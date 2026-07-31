"""
component.py - Component model Pydantic schema for components.yaml.

A component is a reusable software module that wraps one or more drivers
via POSIX interfaces. Components are MCU-independent.

Example components.yaml:
  components:
    - name: shell
      type: shell_cli
      driver: uart2
      config:
        prompt: "hw2c> "
    - name: modbus_rtu
      type: modbus
      driver: uart1
      config:
        slave_id: 1
        timeout_ms: 200
"""

from __future__ import annotations

from typing import Optional, Any
from pydantic import BaseModel, Field, model_validator


class ComponentConfig(BaseModel):
    """A single component instance definition."""

    name: str = Field(..., description="Unique component instance name")
    type: str = Field(..., description="Component type: shell_cli, modbus, etc.")
    driver: str = Field(..., description="Hardware driver instance name to bind to")
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Component-specific configuration parameters",
    )
    task: Optional[str] = Field(
        default=None,
        description="FreeRTOS task to run this component in",
    )
    period_ms: int = Field(
        default=100,
        description="Step period in milliseconds (-1 = event-driven only)",
    )
    priority: int = Field(default=2, description="FreeRTOS task priority")
    stack_size: int = Field(default=512, description="Task stack size in words")


class ComponentsModel(BaseModel):
    """Root model for components.yaml."""

    components: list[ComponentConfig] = Field(
        default_factory=list,
        description="List of component instances",
    )

    @model_validator(mode="after")
    def check_unique_names(self) -> "ComponentsModel":
        names = [c.name for c in self.components]
        duplicates = {n for n in names if names.count(n) > 1}
        if duplicates:
            raise ValueError(f"Duplicate component names: {duplicates}")
        return self
