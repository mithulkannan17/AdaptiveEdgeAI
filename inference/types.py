"""
Inference Data Types

Defines standardized data structures used by the
production inference pipeline.
"""

from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass(slots=True)
class PredictionResult:
    """
    Stores the output of a model prediction.

    Attributes
    ----------
    label:
        Predicted class label.

    class_id:
        Numerical class index.

    confidence:
        Confidence score (0–1).

    top_k:
        List of (label, confidence) tuples sorted by confidence.

    inference_time_ms:
        End-to-end inference latency in milliseconds.
    """

    label: str

    class_id: int

    confidence: float

    top_k: List[Tuple[str, float]] = field(default_factory=list)

    inference_time_ms: float = 0.0