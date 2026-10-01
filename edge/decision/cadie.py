"""
Context-Aware Decision Intelligence Engine

CADIE combines model predictions, environmental
context, event priority, and device state to produce
a context-aware decision.

CADIE does not perform model inference and does not
directly control hardware.
"""

from __future__ import annotations

from typing import Optional

from edge.decision.decision import (
    DecisionResult,
)


class CADIE:
    """
    Context-Aware Decision Intelligence Engine.

    Responsibilities
    ----------------
    1. Evaluate the significance of a detected event.
    2. Combine prediction confidence with event priority.
    3. Consider environmental context.
    4. Consider device/battery state when available.
    5. Produce an explainable decision.
    """

    # --------------------------------------------------
    # Risk thresholds
    # --------------------------------------------------

    LOW_RISK_THRESHOLD = 0.30

    MEDIUM_RISK_THRESHOLD = 0.55

    HIGH_RISK_THRESHOLD = 0.75

    CRITICAL_RISK_THRESHOLD = 0.90

    # --------------------------------------------------
    # Priority normalization
    # --------------------------------------------------

    MAX_EVENT_PRIORITY = 5

    def __init__(
        self,
        critical_priority: int = 5,
        high_priority: int = 4,
    ):
        """
        Parameters
        ----------
        critical_priority:
            Priority at or above this value is considered
            critical.

        high_priority:
            Priority at or above this value is considered
            high importance.
        """

        if critical_priority < 1:

            raise ValueError(
                "critical_priority must be >= 1."
            )

        if high_priority < 1:

            raise ValueError(
                "high_priority must be >= 1."
            )

        if high_priority > critical_priority:

            raise ValueError(
                "high_priority cannot exceed "
                "critical_priority."
            )

        self.critical_priority = (
            critical_priority
        )

        self.high_priority = (
            high_priority
        )

    # ==================================================
    # Utility
    # ==================================================

    @staticmethod
    def _clamp(
        value: float,
        minimum: float = 0.0,
        maximum: float = 1.0,
    ) -> float:
        """
        Clamp a value into the specified range.
        """

        return max(
            minimum,
            min(
                maximum,
                float(value),
            ),
        )

    def _normalize_priority(
        self,
        priority: int,
    ) -> float:
        """
        Convert event priority from 0–5 into 0–1.
        """

        return self._clamp(

            float(priority)
            / self.MAX_EVENT_PRIORITY

        )

    # ==================================================
    # Context Factors
    # ==================================================

    def _environment_factor(
        self,
        profile,
        label: str,
    ) -> float:
        """
        Determine how strongly the current environmental
        context increases the significance of an event.
        """

        environment = (
            profile.environment_type
        )

        # Critical anthropogenic events in natural
        # environments receive additional significance.
        if environment == "Natural":

            if label in {
                "Chainsaw",
                "Fire",
            }:

                return 1.0

            if label in {
                "Bird",
                "Wildlife",
                "Insects",
            }:

                return 0.40

        # Human/mechanical activity is more significant
        # when the environment is predominantly
        # anthropogenic.
        if environment == "Anthropogenic":

            if label in {
                "Chainsaw",
                "EmergencyVehicle",
                "Drill",
                "Jackhammer",
            }:

                return 0.90

            if label in {
                "Human",
                "Vehicle",
            }:

                return 0.70

        if environment == "WeatherDominant":

            if label in {
                "Chainsaw",
                "Fire",
                "EmergencyVehicle",
            }:

                return 0.90

            if label in {
                "Wind",
                "Thunderstorm",
            }:

                return 0.20

        if environment == "Aquatic":

            if label in {
                "Human",
                "Vehicle",
                "Wildlife",
            }:

                return 0.70

            if label == "Water":

                return 0.20

        # Mixed/Unknown/InsufficientData:
        # don't introduce a strong contextual bias.
        return 0.50

    def _battery_factor(
        self,
        battery_percent: Optional[float],
    ) -> float:
        """
        Determine whether battery state should influence
        the decision.

        A low battery does NOT reduce the importance of
        an event. It only modifies operational urgency.
        """

        if battery_percent is None:

            return 1.0

        battery = self._clamp(
            battery_percent,
            0.0,
            100.0,
        )

        if battery <= 10.0:

            return 0.85

        if battery <= 20.0:

            return 0.90

        if battery <= 40.0:

            return 0.95

        return 1.0

    # ==================================================
    # Risk
    # ==================================================

    def _risk_level(
        self,
        score: float,
    ) -> str:
        """
        Convert a decision score into a risk category.
        """

        if score >= self.CRITICAL_RISK_THRESHOLD:

            return "CRITICAL"

        if score >= self.HIGH_RISK_THRESHOLD:

            return "HIGH"

        if score >= self.MEDIUM_RISK_THRESHOLD:

            return "MEDIUM"

        if score >= self.LOW_RISK_THRESHOLD:

            return "LOW"

        return "MINIMAL"

    # ==================================================
    # Action
    # ==================================================

    def _recommended_action(
        self,
        risk_level: str,
        event,
        battery_percent: Optional[float],
    ) -> str:
        """
        Determine the recommended runtime action.
        """

        if not event.detected:

            return "MONITOR"

        if risk_level == "CRITICAL":

            return "TRANSMIT_IMMEDIATELY"

        if risk_level == "HIGH":

            return "TRANSMIT"

        if risk_level == "MEDIUM":

            return "PRIORITIZE"

        # Low-risk events may be suppressed when the
        # device is critically battery constrained.
        if (
            battery_percent is not None
            and battery_percent <= 20.0
        ):

            return "DEFER"

        return "MONITOR"

    def _evaluate_gas_context(
        self,
        device_status: dict,
        gas_assessment: Optional[Any] = None,
    ) -> tuple[float, Optional[str], bool]:
        """
        Extract gas anomaly risk and qualitative factor from telemetry or assessment.
        Returns: (gas_factor, summary_string, is_gas_active)
        """
        # 1. Direct gas assessment object
        if gas_assessment is not None:
            score = float(getattr(gas_assessment, "gas_risk_score", 0.0) if hasattr(gas_assessment, "gas_risk_score") else gas_assessment.get("gas_risk_score", 0.0))
            summary = getattr(gas_assessment, "qualitative_summary", None) if hasattr(gas_assessment, "qualitative_summary") else gas_assessment.get("qualitative_summary")
            return self._clamp(score), summary, True

        # 2. Check device_status dictionary
        if not device_status:
            return 0.0, None, False

        if "gas_assessment" in device_status:
            ga = device_status["gas_assessment"]
            score = float(ga.get("gas_risk_score", 0.0) if isinstance(ga, dict) else getattr(ga, "gas_risk_score", 0.0))
            summary = ga.get("qualitative_summary") if isinstance(ga, dict) else getattr(ga, "qualitative_summary", None)
            return self._clamp(score), summary, True

        if "gas_risk_score" in device_status:
            score = float(device_status["gas_risk_score"])
            return self._clamp(score), f"Atmospheric gas anomaly score: {score:.2f}", True

        # 3. Check raw sensor fields if present
        if "mq2_raw" in device_status or "mq135_raw" in device_status:
            mq2 = float(device_status.get("mq2_raw", 0.0))
            mq135 = float(device_status.get("mq135_raw", 0.0))
            # Basic sanity check if readings indicate active sensors
            if mq2 > 0.0 or mq135 > 0.0:
                score = min(1.0, (mq2 + mq135) / 1000.0)
                return self._clamp(score), "Atmospheric gas telemetry active", True

        return 0.0, None, False

    # ==================================================
    # Main Decision
    # ==================================================

    def evaluate(
        self,
        prediction,
        environment_profile,
        adaptive_policy,
        event,
        device_status: Optional[dict] = None,
        gas_assessment: Optional[Any] = None,
    ) -> DecisionResult:
        """
        Generate a context-aware decision.

        Parameters
        ----------
        prediction:
            PredictionResult.

        environment_profile:
            EnvironmentProfile.

        adaptive_policy:
            AdaptivePolicy.

        event:
            Event produced by EventDetector and
            EventPrioritizer.

        device_status:
            Optional hardware telemetry dictionary.

        gas_assessment:
            Optional GasAnomalyAssessment or dict.
        """

        if prediction is None:

            raise ValueError(
                "prediction cannot be None."
            )

        if environment_profile is None:

            raise ValueError(
                "environment_profile cannot be None."
            )

        if adaptive_policy is None:

            raise ValueError(
                "adaptive_policy cannot be None."
            )

        if event is None:

            raise ValueError(
                "event cannot be None."
            )

        if device_status is None:

            device_status = {}

        # --------------------------------------------------
        # Prediction confidence
        # --------------------------------------------------

        confidence = self._clamp(
            prediction.confidence
        )

        # --------------------------------------------------
        # Event priority
        # --------------------------------------------------

        priority = int(
            getattr(
                event,
                "priority",
                0,
            )
        )

        priority_factor = (
            self._normalize_priority(
                priority
            )
        )

        # --------------------------------------------------
        # Environmental context
        # --------------------------------------------------

        environment_factor = (
            self._environment_factor(

                environment_profile,

                prediction.label,

            )
        )

        # --------------------------------------------------
        # Adaptive sensitivity
        # --------------------------------------------------

        sensitivity = (
            adaptive_policy.sensitivity_for(
                prediction.label
            )
        )

        sensitivity_factor = self._clamp(
            sensitivity / 1.30
        )

        # --------------------------------------------------
        # Battery state
        # --------------------------------------------------

        battery_percent = device_status.get(
            "battery_percent"
        )

        battery_factor = (
            self._battery_factor(
                battery_percent
            )
        )

        # --------------------------------------------------
        # Gas / Atmospheric anomaly state
        # --------------------------------------------------

        gas_factor, gas_summary, is_gas_active = self._evaluate_gas_context(
            device_status=device_status,
            gas_assessment=gas_assessment,
        )

        # --------------------------------------------------
        # Confidence-Driven Primacy & Multimodal Context
        #
        # Prediction confidence is the primary foundation of the
        # decision score and threat triage. Hardware readings
        # (gas anomalies, seismic vibration) provide additive
        # corroboration, but nominal hardware readings NEVER
        # suppress or bottleneck high-confidence acoustic detections.
        # --------------------------------------------------

        # Check vibration from device_status
        vibration_latched = bool(
            device_status.get("vibration_detected", False)
            or device_status.get("vibration", False)
        )

        # Base decision score with confidence primacy (>= 50% weight)
        if is_gas_active:
            score = (
                0.50 * confidence
                + 0.20 * priority_factor
                + 0.12 * environment_factor
                + 0.08 * sensitivity_factor
                + 0.06 * gas_factor
                + 0.04 * battery_factor
            )
            # Additive cross-modal boost: fire acoustic + smoke gas anomaly
            lbl_lower = str(getattr(prediction, "label", "")).lower()
            if any(k in lbl_lower for k in ["fire", "smoke", "burn"]) and gas_factor >= 0.40:
                score = min(1.0, score + 0.12 * gas_factor)
        else:
            score = (
                0.52 * confidence
                + 0.22 * priority_factor
                + 0.12 * environment_factor
                + 0.09 * sensitivity_factor
                + 0.05 * battery_factor
            )

        # Vibration additive corroboration
        if vibration_latched and priority >= self.high_priority:
            score = min(1.0, score + 0.08)

        # --------------------------------------------------
        # Confidence-First Guarantee:
        # High confidence on critical/high-priority threats
        # directly anchors the decision score to ensure alerts
        # are triggered reliably without hardware gating.
        # --------------------------------------------------
        if event.detected and confidence >= 0.85 and priority >= self.high_priority:
            score = max(score, min(1.0, confidence))
        elif event.detected and confidence >= 0.70 and priority >= self.high_priority:
            score = max(score, min(1.0, 0.75 + (confidence - 0.70) * 0.8))

        # Undetected events should never become a high-risk
        # decision simply because of contextual factors.
        if not event.detected:
            score *= 0.35

        score = self._clamp(score)
        risk_level = self._risk_level(score)
        action = self._recommended_action(
            risk_level,
            event,
            battery_percent,
        )

        # --------------------------------------------------
        # Attention
        # --------------------------------------------------

        requires_attention = (
            event.detected
            and (
                risk_level in {"HIGH", "CRITICAL"}
                or (confidence >= 0.80 and priority >= self.high_priority)
            )
        )

        # --------------------------------------------------
        # Explainable factors
        # --------------------------------------------------

        factors = []

        if confidence >= 0.85:
            factors.append(
                f"Primary trigger: High model confidence ({confidence * 100:.1f}%)."
            )
        elif confidence >= 0.65:
            factors.append(
                f"Moderate model confidence ({confidence * 100:.1f}%)."
            )
        else:
            factors.append(
                f"Low model confidence ({confidence * 100:.1f}%)."
            )

        if priority >= self.critical_priority:
            factors.append("Critical event priority.")
        elif priority >= self.high_priority:
            factors.append("High event priority.")

        if environment_factor >= 0.80:
            factors.append(
                "Environmental context increases event significance."
            )

        if is_gas_active and gas_summary:
            factors.append(f"Hardware corroboration: {gas_summary}")

        if vibration_latched:
            factors.append("Hardware corroboration: Vibration sensor triggered.")

        if battery_percent is not None:

            if battery_percent <= 20.0:

                factors.append(
                    "Battery level is critically low."
                )

            elif battery_percent <= 40.0:

                factors.append(
                    "Battery level is reduced."
                )

        if not event.detected:

            factors.append(
                "Event did not pass the adaptive "
                "detection decision."
            )

        # --------------------------------------------------
        # Reason
        # --------------------------------------------------

        if not event.detected:

            reason = (
                "The event was not considered "
                "actionable after adaptive detection."
            )

        elif risk_level == "CRITICAL":

            reason = (
                "High-confidence, high-priority "
                "environmental event requires immediate "
                "attention."
            )

        elif risk_level == "HIGH":

            reason = (
                "The combined prediction confidence, "
                "event priority and environmental context "
                "indicate a significant event."
            )

        elif risk_level == "MEDIUM":

            reason = (
                "The event has moderate contextual "
                "significance and should be prioritized "
                "for continued observation."
            )

        else:

            reason = (
                "The event does not currently indicate "
                "a high-risk environmental condition."
            )

        return DecisionResult(

            risk_level=risk_level,

            decision_score=score,

            recommended_action=action,

            requires_attention=(
                requires_attention
            ),

            confidence=confidence,

            reason=reason,

            contributing_factors=factors,

        )