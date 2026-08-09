"""
Tests for Event Detection & Prioritization.
"""

from edge.events import (
    EventDetector,
    EventPrioritizer,
)

from edge.adaptation import (
    AdaptivePolicy,
)

from inference.types import (
    PredictionResult,
)


def natural_policy():

    return AdaptivePolicy(

        environment_type="Natural",

        detection_threshold=0.55,

        transmission_mode="selective",

        sampling_mode="active",

        class_sensitivity={

            "Bird": 1.20,

            "Chainsaw": 1.30,

            "Wildlife": 1.25,

        },

        class_priority={

            "Bird": 1,

            "Chainsaw": 5,

            "Wildlife": 4,

        },

    )


class TestEventDetector:

    def test_detected_event(self):

        detector = (
            EventDetector()
        )

        prediction = PredictionResult(

            label="Chainsaw",

            class_id=1,

            confidence=0.60,

            inference_time_ms=20.0,

        )

        event = detector.detect(

            prediction,

            natural_policy(),

        )

        assert event.detected is True

        assert (
            event.adjusted_confidence
            == 0.78
        )

        assert (
            event.priority
            == 5
        )

        assert (
            event.environment_type
            == "Natural"
        )

    def test_rejected_event(self):

        detector = (
            EventDetector()
        )

        prediction = PredictionResult(

            label="Bird",

            class_id=0,

            confidence=0.30,

        )

        event = detector.detect(

            prediction,

            natural_policy(),

        )

        assert event.detected is False

        assert event.priority == 0

        assert (
            event.adjusted_confidence
            < event.detection_threshold
        )

    def test_sensitivity_changes_decision(self):

        detector = (
            EventDetector()
        )

        prediction = PredictionResult(

            label="Chainsaw",

            class_id=1,

            confidence=0.45,

        )

        event = detector.detect(

            prediction,

            natural_policy(),

        )

        # 0.45 × 1.30 = 0.585
        # threshold = 0.55

        assert event.detected is True

    def test_ignored_class(self):

        policy = AdaptivePolicy(

            environment_type="Natural",

            detection_threshold=0.55,

            transmission_mode="selective",

            sampling_mode="active",

            class_sensitivity={
                "Bird": 1.20,
            },

            class_priority={
                "Bird": 1,
            },

            ignored_classes=(
                "Bird",
            ),

        )

        prediction = PredictionResult(

            label="Bird",

            class_id=0,

            confidence=0.99,

        )

        event = (
            EventDetector()
            .detect(
                prediction,
                policy,
            )
        )

        assert event.detected is False

        assert event.priority == 0

        assert (
            "ignored"
            in event.reason.lower()
        )

    def test_event_serialization(self):

        event = (
            EventDetector()
            .detect(

                PredictionResult(

                    label="Chainsaw",

                    class_id=1,

                    confidence=0.60,

                ),

                natural_policy(),

            )
        )

        data = event.to_dict()

        assert isinstance(
            data,
            dict
        )

        assert (
            data["label"]
            == "Chainsaw"
        )

        assert (
            "adjusted_confidence"
            in data
        )


class TestEventPrioritizer:

    def test_critical_priority(self):

        detector = (
            EventDetector()
        )

        prioritizer = (
            EventPrioritizer()
        )

        prediction = PredictionResult(

            label="Chainsaw",

            class_id=1,

            confidence=0.80,

        )

        policy = natural_policy()

        event = detector.detect(
            prediction,
            policy,
        )

        prioritized = (
            prioritizer.prioritize(
                event,
                policy,
            )
        )

        assert (
            prioritized.priority
            == EventPrioritizer.CRITICAL
        )

    def test_high_priority(self):

        policy = AdaptivePolicy(

            environment_type="Natural",

            detection_threshold=0.55,

            transmission_mode="selective",

            sampling_mode="active",

            class_sensitivity={
                "Wildlife": 1.25,
            },

            class_priority={
                "Wildlife": 4,
            },

        )

        prediction = PredictionResult(

            label="Wildlife",

            class_id=12,

            confidence=0.80,

        )

        detector = (
            EventDetector()
        )

        prioritizer = (
            EventPrioritizer()
        )

        event = detector.detect(
            prediction,
            policy,
        )

        prioritized = (
            prioritizer.prioritize(
                event,
                policy,
            )
        )

        assert (
            prioritized.priority
            == EventPrioritizer.HIGH
        )

    def test_undetected_event_remains_priority_zero(
        self,
    ):

        policy = natural_policy()

        prediction = PredictionResult(

            label="Bird",

            class_id=0,

            confidence=0.10,

        )

        detector = (
            EventDetector()
        )

        prioritizer = (
            EventPrioritizer()
        )

        event = detector.detect(
            prediction,
            policy,
        )

        prioritized = (
            prioritizer.prioritize(
                event,
                policy,
            )
        )

        assert (
            prioritized.detected
            is False
        )

        assert (
            prioritized.priority
            == 0
        )