"""
Edge Runtime Package.

Provides the runtime orchestration layer that connects
inference, unknown-sound discovery, environmental profiling,
adaptive behaviour, and event prioritization.
"""

from edge.runtime.edge_controller import (
    EdgeController,
    EdgeRuntimeResult,
)


__all__ = [
    "EdgeController",
    "EdgeRuntimeResult",
]