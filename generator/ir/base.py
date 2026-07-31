"""
base.py - Base class for all IR objects.

Provides `to_dict()` for backward compatibility with the legacy flat-dict
context that Jinja2 templates currently consume.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict


@dataclass
class IRObject:
    """Base class for all IR dataclass objects.

    Subclasses inherit the `to_dict()` method which recursively converts
    the IR tree into a plain dict suitable for Jinja2's `.render(**kwargs)`.
    """

    def to_dict(self) -> dict:
        """Recursively convert IR to dict, stripping None values.

        Handles nested IRObject, list[IRObject], and plain values.
        """
        result = {}
        for k, v in asdict(self).items():
            if v is None:
                continue
            if isinstance(v, IRObject):
                result[k] = v.to_dict()
            elif isinstance(v, list):
                result[k] = [
                    item.to_dict() if isinstance(item, IRObject) else item
                    for item in v
                ]
            elif isinstance(v, dict):
                result[k] = {
                    dk: dv.to_dict() if isinstance(dv, IRObject) else dv
                    for dk, dv in v.items()
                }
            else:
                result[k] = v
        return result
