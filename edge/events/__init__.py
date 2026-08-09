"""
Event Detection and Prioritization Package.

Provides the Event Detection & Prioritization Engine
(AEPE) used by the adaptive edge intelligence system.
"""

from edge.events.event import Event

from edge.events.event_detector import (
    EventDetector,
)

from edge.events.event_prioritizer import (
    EventPrioritizer,
)


__all__ = [
    "Event",
    "EventDetector",
    "EventPrioritizer",
]