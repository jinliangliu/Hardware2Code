"""
bind.py - Pydantic v2 models for bind.yaml (hardware ⇔ software wiring).
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class BindInterrupt(BaseModel):
    """Pin interrupt → task binding."""
    model_config = ConfigDict(extra="allow")
    pin: str
    task: str
    event: str = ""


class BindPeripheralAssign(BaseModel):
    """Peripheral → task ownership assignment."""
    model_config = ConfigDict(extra="allow")
    peripheral: str
    task: str
    role: str = ""


class BindRouting(BaseModel):
    """Task → task communication route."""
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    from_task: str = Field(alias="from")
    to: Optional[str] = None
    signal: str
    condition: Optional[str] = None


class BindModel(BaseModel):
    """Top-level bind.yaml model."""
    model_config = ConfigDict(extra="allow")
    version: int = 1
    hardware: str = "hardware.yaml"
    task: str = "task.yaml"
    interrupt: list[BindInterrupt] = []
    peripheral_assign: list[BindPeripheralAssign] = []
    routing: list[BindRouting] = []
