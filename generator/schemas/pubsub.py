"""
pubsub.py - Publish/Subscribe topic schema for pubsub.yaml.

Topics define named data channels for inter-component communication.
Each component can publish to and/or subscribe to topics.

Example pubsub.yaml:
  topics:
    - name: temperature
      description: "Temperature readings (scaled to int32, unit=0.1C)"
    - name: button_state
      description: "Button press/release (0=release, 1=press)"
    - name: alarm_trigger
      description: "Alarm trigger with alarm_id as value"
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class TopicConfig(BaseModel):
    """A single topic definition."""

    name: str = Field(..., description="Unique topic name (snake_case)")
    description: str = Field(
        default="",
        description="Human-readable topic description",
    )


class PubSubModel(BaseModel):
    """Root model for pubsub.yaml."""

    topics: list[TopicConfig] = Field(
        default_factory=list,
        description="List of pub/sub topics",
    )

    @model_validator(mode="after")
    def check_unique_names(self) -> "PubSubModel":
        names = [t.name for t in self.topics]
        duplicates = {n for n in names if names.count(n) > 1}
        if duplicates:
            raise ValueError(f"Duplicate topic names: {duplicates}")
        return self
