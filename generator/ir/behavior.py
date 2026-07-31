"""
behavior.py - State machine behavior IR.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import IRObject


@dataclass
class BehaviorIR(IRObject):
    """Parsed state machine behavior from task.yaml."""

    initial_state: str = ""
    states: list[dict] = field(default_factory=list)
    regions: list[dict] = field(default_factory=list)
    variables: list[dict] = field(default_factory=list)
    raw: dict = field(default_factory=dict)  # full dict for template compat
