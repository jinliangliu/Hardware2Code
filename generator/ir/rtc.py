"""
rtc.py - RTC configuration IR.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import IRObject


@dataclass
class RtcAlarmIR(IRObject):
    """Single RTC alarm entry."""

    type: str = "periodic_sec"   # periodic_sec/min/hour | one_shot | one_shot_ms
    period_ms: int = 0
    event: str = ""


@dataclass
class RtcInitTimeIR(IRObject):
    """Parsed RTC initial time."""

    year: int = 0
    month: int = 1
    day: int = 1
    hour: int = 0
    min: int = 0
    sec: int = 0


@dataclass
class RtcIR(IRObject):
    """RTC peripheral configuration."""

    has_rtc: bool = False
    clock_source: str = "LSI"
    async_prediv: int = 127
    sync_prediv: int = 255
    wakeup_interval_ms: int = 1000
    alarms: list[RtcAlarmIR] = field(default_factory=list)
    init_time: RtcInitTimeIR = field(default_factory=RtcInitTimeIR)
