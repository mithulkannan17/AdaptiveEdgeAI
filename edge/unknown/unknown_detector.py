"""
Unknown Sound Detector

Determines whether a model prediction should be
accepted as a known event or rejected as unknown.

Detection signals:

    1. Maximum class probability
    2. Top-2 prediction margin
    3. Optional acoustic activity / RMS

The confidence and margin logic remains the
primary open-set mechanism.

The acoustic activity gate prevents pathological
cases such as complete silence being accepted as
a highly confident known class.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UnknownDecision:
    """
    Result of open-set sound detection.
    """

    is_unknown: bool

    predicted_class: int

    confidence: float

    margin: float

    reason: str

    # Optional acoustic information.
    #
    # None means that the caller did not provide an
    # audio-energy measurement.
    audio_rms: float | None = None

    def to_dict(self) -> dict:
        """
        Convert decision to a serializable dictionary.
        """

        return {
            "is_unknown": self.is_unknown,

            "predicted_class":
                self.predicted_class,

            "confidence":
                self.confidence,

            "margin":
                self.margin,

            "reason":
                self.reason,

            "audio_rms":
                self.audio_rms,
        }


class UnknownDetector:
    """
    Multi-signal open-set detector.

    Detection signals:

        1. Maximum class probability.
        2. Margin between the top two classes.
        3. Optional audio RMS activity.

    Decision logic:

        Low confidence
            → Unknown

        Low prediction margin
            → Unknown

        Explicitly supplied near-silence
            → Unknown

        Otherwise
            → Known

    The acoustic activity check is optional so that
    existing callers remain backward compatible.
    """

    def __init__(
        self,
        confidence_threshold: float = 0.60,
        margin_threshold: float = 0.15,
        audio_rms_threshold: float = 0.001,
    ):
        # --------------------------------------------------
        # Validate confidence threshold
        # --------------------------------------------------

        if not 0.0 <= confidence_threshold <= 1.0:

            raise ValueError(
                "confidence_threshold must be "
                "between 0 and 1."
            )

        # --------------------------------------------------
        # Validate margin threshold
        # --------------------------------------------------

        if not 0.0 <= margin_threshold <= 1.0:

            raise ValueError(
                "margin_threshold must be "
                "between 0 and 1."
            )

        # --------------------------------------------------
        # Validate acoustic threshold
        # --------------------------------------------------

        if audio_rms_threshold < 0.0:

            raise ValueError(
                "audio_rms_threshold must be "
                "greater than or equal to zero."
            )

        self.confidence_threshold = (
            float(confidence_threshold)
        )

        self.margin_threshold = (
            float(margin_threshold)
        )

        self.audio_rms_threshold = (
            float(audio_rms_threshold)
        )

    # ======================================================
    # PROBABILITY VALIDATION
    # ======================================================

    @staticmethod
    def _validate_probabilities(
        probabilities,
    ) -> list[float]:
        """
        Validate and normalize class probabilities.
        """

        if probabilities is None:

            raise ValueError(
                "probabilities cannot be None."
            )

        try:

            probabilities = [
                float(value)
                for value in probabilities
            ]

        except (TypeError, ValueError) as exc:

            raise ValueError(
                "probabilities must contain "
                "numeric values."
            ) from exc

        if len(probabilities) < 2:

            raise ValueError(
                "At least two class probabilities "
                "are required."
            )

        if any(
            value < 0.0 or value > 1.0
            for value in probabilities
        ):

            raise ValueError(
                "Probabilities must be between "
                "0 and 1."
            )

        return probabilities

    # ======================================================
    # AUDIO RMS VALIDATION
    # ======================================================

    def _validate_audio_rms(
        self,
        audio_rms,
    ) -> float | None:
        """
        Validate an optional audio RMS value.

        None means that acoustic information is not
        available and therefore the acoustic gate is
        skipped.
        """

        if audio_rms is None:
            return None

        try:

            audio_rms = float(
                audio_rms
            )

        except (TypeError, ValueError) as exc:

            raise ValueError(
                "audio_rms must be numeric or None."
            ) from exc

        if audio_rms < 0.0:

            raise ValueError(
                "audio_rms must be greater than "
                "or equal to zero."
            )

        return audio_rms

    # ======================================================
    # DECISION
    # ======================================================

    def decide(
        self,
        probabilities,
        audio_rms: float | None = None,
    ) -> UnknownDecision:
        """
        Decide whether a probability distribution
        represents a known or unknown event.

        Parameters
        ----------
        probabilities:
            Iterable of class probabilities.

        audio_rms:
            Optional normalized waveform RMS.

            For normalized float32 PCM audio:

                silence ≈ 0.0

            A value below `audio_rms_threshold`
            is treated as insufficient acoustic activity.

            If None, the acoustic gate is skipped.

        Returns
        -------
        UnknownDecision
        """

        # --------------------------------------------------
        # Validate probabilities
        # --------------------------------------------------

        probabilities = (
            self._validate_probabilities(
                probabilities
            )
        )

        # --------------------------------------------------
        # Validate optional acoustic information
        # --------------------------------------------------

        audio_rms = (
            self._validate_audio_rms(
                audio_rms
            )
        )

        # --------------------------------------------------
        # Rank predictions
        # --------------------------------------------------

        ranked = sorted(
            enumerate(probabilities),
            key=lambda item: item[1],
            reverse=True,
        )

        top_class, top_probability = (
            ranked[0]
        )

        second_probability = (
            ranked[1][1]
        )

        margin = (
            top_probability
            - second_probability
        )

        # --------------------------------------------------
        # Rule 1:
        # Low classification confidence
        # --------------------------------------------------

        if (
            top_probability
            < self.confidence_threshold
        ):

            return UnknownDecision(

                is_unknown=True,

                predicted_class=top_class,

                confidence=top_probability,

                margin=margin,

                reason=(
                    "Low classification confidence."
                ),

                audio_rms=audio_rms,
            )

        # --------------------------------------------------
        # Rule 2:
        # Low prediction margin
        # --------------------------------------------------

        if (
            margin
            < self.margin_threshold
        ):

            return UnknownDecision(

                is_unknown=True,

                predicted_class=top_class,

                confidence=top_probability,

                margin=margin,

                reason=(
                    "Low prediction margin between "
                    "top competing classes."
                ),

                audio_rms=audio_rms,
            )

        # --------------------------------------------------
        # Rule 3:
        # Acoustic inactivity
        #
        # IMPORTANT:
        #
        # This rule only runs when audio_rms is supplied.
        #
        # Therefore existing callers that only provide
        # probabilities remain fully compatible.
        # --------------------------------------------------

        if (
            audio_rms is not None
            and audio_rms
            <= self.audio_rms_threshold
        ):

            return UnknownDecision(

                is_unknown=True,

                predicted_class=top_class,

                confidence=top_probability,

                margin=margin,

                reason=(
                    "Insufficient acoustic activity; "
                    "audio is effectively silent."
                ),

                audio_rms=audio_rms,
            )

        # --------------------------------------------------
        # Known prediction
        # --------------------------------------------------

        if audio_rms is None:

            reason = (
                "Prediction exceeds confidence "
                "and margin thresholds."
            )

        else:

            reason = (
                "Prediction exceeds confidence and "
                "margin thresholds and contains "
                "sufficient acoustic activity."
            )

        return UnknownDecision(

            is_unknown=False,

            predicted_class=top_class,

            confidence=top_probability,

            margin=margin,

            reason=reason,

            audio_rms=audio_rms,
        )

    # ======================================================
    # CONFIGURATION
    # ======================================================

    def get_config(self) -> dict:
        """
        Return detector configuration for dashboards,
        diagnostics and runtime inspection.
        """

        return {
            "confidence_threshold":
                self.confidence_threshold,

            "margin_threshold":
                self.margin_threshold,

            "audio_rms_threshold":
                self.audio_rms_threshold,
        }