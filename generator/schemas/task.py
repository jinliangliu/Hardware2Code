"""
task.py - Pydantic v2 models for task.yaml (software architecture).
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class ProjectModel(BaseModel):
    """Project metadata."""
    model_config = ConfigDict(extra="allow")
    name: str = "untitled"
    version: str = "0.1.0"


class AppTaskModel(BaseModel):
    """FreeRTOS task definition (simplified — triggers/signals in bind.yaml)."""
    model_config = ConfigDict(extra="allow")
    name: str
    priority: int = 1
    stack_size: int = 128


class VariableModel(BaseModel):
    """Global variable declaration."""
    model_config = ConfigDict(extra="allow")
    name: str
    type: str
    array: Optional[int] = None
    initial: Any = None


class StructFieldModel(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    type: Optional[str] = None
    array: Optional[int] = None
    fields: Optional[list["StructFieldModel"]] = None


class EnumValueModel(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    value: Optional[int] = None


class UnionFieldModel(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    type: str
    array: Optional[int] = None


class BitfieldFieldModel(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    width: int


class TypeDefModel(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    struct: Optional[list[StructFieldModel]] = None
    enum: Optional[list[EnumValueModel]] = None
    union: Optional[list[UnionFieldModel]] = None
    bitfield: Optional[list[BitfieldFieldModel]] = None


class BehaviorModel(BaseModel):
    """State-machine DSL (moved from old hardware.yaml to task.yaml)."""
    model_config = ConfigDict(extra="allow")
    initial_state: Optional[str] = None
    variables: list[VariableModel] = []
    types: list[TypeDefModel] = []
    events: list[dict] = []
    states: list[dict] = []
    regions: list[dict] = []


class TaskModel(BaseModel):
    """Top-level task.yaml model."""
    model_config = ConfigDict(extra="allow")
    project: ProjectModel = Field(default_factory=ProjectModel)
    app_tasks: list[AppTaskModel] = []
    behavior: Optional[BehaviorModel] = None
