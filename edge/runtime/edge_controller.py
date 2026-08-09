"""
Edge Runtime Controller

Orchestrates the complete edge intelligence pipeline.

The controller connects:

    PredictionResult
        ↓
    Environmental Profiling
        ↓
    Adaptive Behaviour
        ↓
    Event Detection
        ↓
    Event Prioritization

Unknown-sound discovery is executed alongside the normal
event pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from inference.predictor import Predictor
from inference.types import PredictionResult

from edge.adaptation import (
    AdaptiveBehaviorEngine,
    AdaptivePolicy,
)

from edge.events import (
    Event,
    EventDetector,
    EventPrioritizer,
)

from edge.profiling import (
    EnvironmentProfile,
    EnvironmentalProfiler,
)


@dataclass
class EdgeRuntimeResult:
    """
    Complete result produced by the edge runtime.

    Contains the model prediction, environmental context,
    adaptive policy, event decision, prioritized event,
    and optional unknown-discovery result.
    """

    prediction: PredictionResult

    environment_profile: EnvironmentProfile

    adaptive_policy: AdaptivePolicy

    event: Event

    discovery_result: object | None = None

    def to_dict(self) -> dict:
        """
        Convert the complete runtime result into a
        serializable dictionary.
        """

        discovery = None

        if self.discovery_result is not None:

            if hasattr(
                self.discovery_result,
                "to_dict",
            ):

                discovery = (
                    self.discovery_result.to_dict()
                )

            else:

                discovery = str(
                    self.discovery_result
                )

        return {

            "prediction": {

                "label":
                    self.prediction.label,

                "class_id":
                    self.prediction.class_id,

                "confidence":
                    self.prediction.confidence,

                "top_k":
                    list(
                        self.prediction.top_k
                    ),

                "inference_time_ms":
                    self.prediction.inference_time_ms,

            },

            "environment_profile":
                self.environment_profile.to_dict(),

            "adaptive_policy":
                self.adaptive_policy.to_dict(),

            "event":
                self.event.to_dict(),

            "discovery_result":
                discovery,

        }


class EdgeController:
    """
    Main runtime orchestrator for the adaptive edge node.

    The controller does not implement the individual
    intelligence algorithms. It coordinates the already
    tested subsystems.
    """

    def __init__(
        self,
        predictor: Predictor,
        profiler: EnvironmentalProfiler | None = None,
        behavior_engine: AdaptiveBehaviorEngine | None = None,
        event_detector: EventDetector | None = None,
        event_prioritizer: EventPrioritizer | None = None,
    ):
        """
        Parameters
        ----------
        predictor:
            Production inference Predictor.

        profiler:
            Environmental profiling engine.

        behavior_engine:
            Adaptive behaviour engine.

        event_detector:
            Adaptive event detector.

        event_prioritizer:
            Event prioritization engine.
        """

        if predictor is None:

            raise ValueError(
                "predictor cannot be None."
            )

        self.predictor = predictor

        self.profiler = (

            profiler

            if profiler is not None

            else EnvironmentalProfiler()

        )

        self.behavior_engine = (

            behavior_engine

            if behavior_engine is not None

            else AdaptiveBehaviorEngine()

        )

        self.event_detector = (

            event_detector

            if event_detector is not None

            else EventDetector()

        )

        self.event_prioritizer = (

            event_prioritizer

            if event_prioritizer is not None

            else EventPrioritizer()

        )

        self.last_result: EdgeRuntimeResult | None = None

    # ======================================================
    # Process Spectrogram
    # ======================================================

    def process_spectrogram(
        self,
        spectrogram,
        top_k: int = 5,
        audio_path: str | Path | None = None,
    ) -> EdgeRuntimeResult:
        """
        Run the complete edge intelligence pipeline
        on a model-ready spectrogram.

        Parameters
        ----------
        spectrogram:
            Model-ready spectrogram.

        top_k:
            Number of top model predictions.

        audio_path:
            Optional source audio path.

        Returns
        -------
        EdgeRuntimeResult
            Complete edge decision.
        """

        prediction = (
            self.predictor.predict_spectrogram(

                spectrogram,

                top_k=top_k,

                audio_path=audio_path,

            )
        )

        return self.process_prediction(
            prediction
        )

    # ======================================================
    # Process Prediction
    # ======================================================

    def process_prediction(
        self,
        prediction: PredictionResult,
    ) -> EdgeRuntimeResult:
        """
        Process an existing PredictionResult through
        environmental profiling, adaptive behaviour,
        event detection, and prioritization.

        This method is useful when inference has already
        been performed separately.
        """

        if not isinstance(
            prediction,
            PredictionResult,
        ):

            raise TypeError(
                "prediction must be a PredictionResult."
            )

        # --------------------------------------------------
        # Environmental profiling
        # --------------------------------------------------

        self.profiler.add_event(

            label=prediction.label,

            confidence=prediction.confidence,

        )

        profile = (
            self.profiler.profile()
        )

        # --------------------------------------------------
        # Adaptive policy
        # --------------------------------------------------

        policy = (
            self.behavior_engine.generate_policy(
                profile
            )
        )

        # --------------------------------------------------
        # Event detection
        # --------------------------------------------------

        event = (
            self.event_detector.detect(

                prediction,

                policy,

            )
        )

        # --------------------------------------------------
        # Event prioritization
        # --------------------------------------------------

        event = (
            self.event_prioritizer.prioritize(

                event,

                policy,

            )
        )

        # --------------------------------------------------
        # Unknown discovery
        #
        # Unknown discovery is already performed by
        # Predictor during predict_spectrogram().
        #
        # We retrieve the latest result here.
        # --------------------------------------------------

        discovery_result = (

            self.predictor
            .get_last_discovery_result()

        )

        # --------------------------------------------------
        # Runtime result
        # --------------------------------------------------

        result = EdgeRuntimeResult(

            prediction=prediction,

            environment_profile=profile,

            adaptive_policy=policy,

            event=event,

            discovery_result=(
                discovery_result
            ),

        )

        self.last_result = result

        return result

    # ======================================================
    # Current Result
    # ======================================================

    def get_last_result(
        self,
    ) -> EdgeRuntimeResult | None:
        """
        Return the most recent runtime result.
        """

        return self.last_result

    # ======================================================
    # Reset
    # ======================================================

    def reset(
        self,
    ) -> None:
        """
        Reset the environmental profiling state and
        runtime result.

        Unknown discovery buffering is also cleared.
        """

        self.profiler.reset()

        self.predictor.clear_unknown_buffer()

        self.last_result = None

    # ======================================================
    # State
    # ======================================================

    def state(
        self,
    ) -> dict | None:
        """
        Return the latest runtime state as a dictionary.
        """

        if self.last_result is None:

            return None

        return (
            self.last_result.to_dict()
        )