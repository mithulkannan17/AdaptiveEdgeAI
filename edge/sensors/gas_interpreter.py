"""
MQ-2 / MQ-135 Gas Sensor Interpreter & Environmental Anomaly Engine.

Scientific & Operational Principles:
-------------------------------------
1. Calibration Integrity:
   - MQ-2 (Combustion/Smoke/LPG) and MQ-135 (Air Quality/Ammonia/CO/CO2) are
     metal oxide semiconductor (MOS) sensors without factory individual PPM curves.
   - We explicitly DO NOT report uncalibrated exact PPM values.
   - Instead, we track dynamic rolling baselines, detect relative anomaly ratios,
     and compute statistical rate-of-change (trends).

2. Real-Time Anomaly Scoring:
   - Ratio = Raw_ADC / Rolling_Baseline_ADC.
   - Ratio < 1.15 : NOMINAL (clean ambient baseline)
   - 1.15 <= Ratio < 1.40 : ADVISORY (slight gas presence or sensor drift)
   - 1.40 <= Ratio < 2.00 : ELEVATED (distinct smoke/gas detection)
   - Ratio >= 2.00 : CRITICAL (heavy smoke or combustion anomaly)

3. Multimodal Acoustic-Gas Cross Validation:
   - Evaluates whether acoustic events (e.g. Fire, Combustion, Machinery)
     are corroborated by atmospheric gas sensor changes.
   - Boosts CADIE risk when acoustic & atmospheric cues co-occur.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
import math
import time
from typing import Any, Deque, Dict, List, Optional, Tuple


class GasTrend(str, Enum):
    """Rate-of-change trend category for gas sensors."""
    RISING_FAST = "RISING_FAST"
    RISING = "RISING"
    STABLE = "STABLE"
    FALLING = "FALLING"


@dataclass
class GasSensorReading:
    """Individual timestamped sample from one gas sensor channel."""
    raw_adc: float
    voltage: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class GasAnomalyAssessment:
    """Consolidated assessment of multi-sensor gas telemetry."""
    # Anomaly scores [0.0, 1.0]
    gas_risk_score: float
    mq2_anomaly_score: float
    mq135_anomaly_score: float

    # Status classifications: NOMINAL, ADVISORY, ELEVATED, CRITICAL
    mq2_status: str
    mq135_status: str
    overall_status: str

    # Metrics
    mq2_ratio_to_baseline: float
    mq135_ratio_to_baseline: float
    mq2_trend: GasTrend
    mq135_trend: GasTrend

    # Flags
    smoke_cue_detected: bool
    gas_anomaly_detected: bool
    baseline_calibrated: bool

    # Human-readable rationale
    qualitative_summary: str
    contributing_factors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert assessment to dictionary format for APIs and CADIE."""
        return {
            "gas_risk_score": round(self.gas_risk_score, 4),
            "mq2_anomaly_score": round(self.mq2_anomaly_score, 4),
            "mq135_anomaly_score": round(self.mq135_anomaly_score, 4),
            "mq2_status": self.mq2_status,
            "mq135_status": self.mq135_status,
            "overall_status": self.overall_status,
            "mq2_ratio": round(self.mq2_ratio_to_baseline, 3),
            "mq135_ratio": round(self.mq135_ratio_to_baseline, 3),
            "mq2_trend": self.mq2_trend.value,
            "mq135_trend": self.mq135_trend.value,
            "smoke_cue_detected": self.smoke_cue_detected,
            "gas_anomaly_detected": self.gas_anomaly_detected,
            "baseline_calibrated": self.baseline_calibrated,
            "qualitative_summary": self.qualitative_summary,
            "contributing_factors": self.contributing_factors,
        }


class ChannelBaselineTracker:
    """
    Maintains a rolling statistical baseline and trend estimator for a single sensor channel.
    """

    def __init__(
        self,
        window_size: int = 60,
        trend_window_size: int = 10,
        warmup_samples: int = 10,
        fast_rise_threshold: float = 0.05,  # 5% change per sample
        moderate_rise_threshold: float = 0.015,  # 1.5% change per sample
    ):
        self.window_size = window_size
        self.trend_window_size = trend_window_size
        self.warmup_samples = warmup_samples
        self.fast_rise_threshold = fast_rise_threshold
        self.moderate_rise_threshold = moderate_rise_threshold

        self.history: Deque[GasSensorReading] = deque(maxlen=window_size)
        self.baseline_adc: Optional[float] = None

    def update(self, raw_adc: float, voltage: float, timestamp: Optional[float] = None) -> Tuple[float, GasTrend, float]:
        """
        Record new reading and return (ratio_to_baseline, trend, anomaly_score).
        """
        ts = timestamp if timestamp is not None else time.time()
        reading = GasSensorReading(raw_adc=raw_adc, voltage=voltage, timestamp=ts)
        self.history.append(reading)

        # Baseline calculation: use 20th percentile (lowest clean ambient readings) or mean of lowest half
        all_raw = [r.raw_adc for r in self.history]
        sorted_raw = sorted(all_raw)
        
        # Take mean of bottom 30% of window as ambient clean-air baseline
        cutoff_idx = max(1, int(len(sorted_raw) * 0.30))
        ambient_baseline = float(np_mean(sorted_raw[:cutoff_idx]))
        self.baseline_adc = max(1.0, ambient_baseline)

        # Ratio to baseline
        ratio = max(0.0, raw_adc / self.baseline_adc)

        # Trend estimation using linear slope across recent trend window
        trend = self._estimate_trend()

        # Score mapping [0.0, 1.0]
        score = self._compute_anomaly_score(ratio, trend)

        return ratio, trend, score

    def _estimate_trend(self) -> GasTrend:
        """Estimate rate-of-change over the recent trend window."""
        if len(self.history) < 3:
            return GasTrend.STABLE

        recent = list(self.history)[-self.trend_window_size:]
        if len(recent) < 2:
            return GasTrend.STABLE

        y = [r.raw_adc for r in recent]
        x = list(range(len(y)))
        n = len(y)

        # Simple linear regression slope
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        denom = sum((xi - mean_x) ** 2 for xi in x)
        if denom == 0:
            return GasTrend.STABLE

        slope = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n)) / denom

        # Normalize slope relative to baseline
        rel_slope = slope / max(self.baseline_adc or 1.0, 1.0)

        if rel_slope >= self.fast_rise_threshold:
            return GasTrend.RISING_FAST
        elif rel_slope >= self.moderate_rise_threshold:
            return GasTrend.RISING
        elif rel_slope <= -self.moderate_rise_threshold:
            return GasTrend.FALLING
        else:
            return GasTrend.STABLE

    def _compute_anomaly_score(self, ratio: float, trend: GasTrend) -> float:
        """Map ratio and trend to continuous score [0.0, 1.0]."""
        # Baseline ratio curve:
        # ratio 1.0 -> 0.0
        # ratio 1.4 -> 0.4
        # ratio 2.0 -> 0.8
        # ratio >= 2.5 -> 1.0
        if ratio <= 1.0:
            base_score = 0.0
        elif ratio < 1.4:
            base_score = 0.40 * ((ratio - 1.0) / 0.40)
        elif ratio < 2.0:
            base_score = 0.40 + 0.40 * ((ratio - 1.4) / 0.60)
        else:
            base_score = min(1.0, 0.80 + 0.20 * ((ratio - 2.0) / 0.50))

        # Trend bonus
        trend_bonus = 0.0
        if trend == GasTrend.RISING_FAST:
            trend_bonus = 0.15
        elif trend == GasTrend.RISING:
            trend_bonus = 0.08
        elif trend == GasTrend.FALLING:
            trend_bonus = -0.05

        return max(0.0, min(1.0, base_score + trend_bonus))

    @property
    def is_calibrated(self) -> bool:
        return len(self.history) >= self.warmup_samples


def np_mean(values: List[float]) -> float:
    """Helper mean function without hard dependency on numpy."""
    if not values:
        return 0.0
    return sum(values) / len(values)


class GasSensorInterpreter:
    """
    Multi-node manager and interpreter for MQ-2 (Smoke/LPG) and MQ-135 (Air Quality/CO).
    """

    def __init__(
        self,
        window_size: int = 60,
        trend_window_size: int = 10,
        warmup_samples: int = 10,
        advisory_threshold: float = 1.15,
        elevated_threshold: float = 1.40,
        critical_threshold: float = 2.00,
    ):
        self.window_size = window_size
        self.trend_window_size = trend_window_size
        self.warmup_samples = warmup_samples

        self.advisory_threshold = advisory_threshold
        self.elevated_threshold = elevated_threshold
        self.critical_threshold = critical_threshold

        # Device-specific trackers: device_id -> { "mq2": tracker, "mq135": tracker }
        self._trackers: Dict[str, Dict[str, ChannelBaselineTracker]] = {}

    def _get_or_create_trackers(self, device_id: str) -> Dict[str, ChannelBaselineTracker]:
        if device_id not in self._trackers:
            self._trackers[device_id] = {
                "mq2": ChannelBaselineTracker(
                    window_size=self.window_size,
                    trend_window_size=self.trend_window_size,
                    warmup_samples=self.warmup_samples,
                ),
                "mq135": ChannelBaselineTracker(
                    window_size=self.window_size,
                    trend_window_size=self.trend_window_size,
                    warmup_samples=self.warmup_samples,
                ),
            }
        return self._trackers[device_id]

    def update(
        self,
        device_id: str,
        mq2_raw: float,
        mq2_voltage: float,
        mq135_raw: float,
        mq135_voltage: float,
        timestamp: Optional[float] = None,
    ) -> GasAnomalyAssessment:
        """
        Ingest telemetry readings for a device and produce an anomaly assessment.
        """
        trackers = self._get_or_create_trackers(device_id)

        # Update channels
        mq2_ratio, mq2_trend, mq2_score = trackers["mq2"].update(mq2_raw, mq2_voltage, timestamp)
        mq135_ratio, mq135_trend, mq135_score = trackers["mq135"].update(mq135_raw, mq135_voltage, timestamp)

        # Combined gas risk score (MQ-2 weighted 55% for direct smoke/fire, MQ-135 45% for combustion products)
        combined_score = (0.55 * mq2_score) + (0.45 * mq135_score)

        # Status classifications
        mq2_status = self._classify_status(mq2_ratio)
        mq135_status = self._classify_status(mq135_ratio)
        overall_status = self._classify_overall_status(combined_score, mq2_status, mq135_status)

        # Detection flags
        smoke_cue = (mq2_ratio >= self.elevated_threshold) or (mq2_trend == GasTrend.RISING_FAST and mq2_ratio >= self.advisory_threshold)
        gas_anomaly = (combined_score >= 0.35) or (mq2_status in ("ELEVATED", "CRITICAL")) or (mq135_status in ("ELEVATED", "CRITICAL"))
        calibrated = trackers["mq2"].is_calibrated and trackers["mq135"].is_calibrated

        # Build qualitative description and contributing factors
        factors: List[str] = []
        if mq2_ratio >= self.elevated_threshold:
            factors.append(f"MQ-2 (Smoke/Combustion) elevated ({mq2_ratio:.2f}x baseline, trend: {mq2_trend.value})")
        elif mq2_ratio >= self.advisory_threshold:
            factors.append(f"MQ-2 advisory level ({mq2_ratio:.2f}x baseline)")

        if mq135_ratio >= self.elevated_threshold:
            factors.append(f"MQ-135 (Air Quality/CO) elevated ({mq135_ratio:.2f}x baseline, trend: {mq135_trend.value})")
        elif mq135_ratio >= self.advisory_threshold:
            factors.append(f"MQ-135 advisory level ({mq135_ratio:.2f}x baseline)")

        if not factors:
            factors.append("Atmospheric gas readings within nominal ambient baseline")

        summary = self._build_summary(overall_status, mq2_ratio, mq135_ratio, mq2_trend, mq135_trend, smoke_cue)

        return GasAnomalyAssessment(
            gas_risk_score=combined_score,
            mq2_anomaly_score=mq2_score,
            mq135_anomaly_score=mq135_score,
            mq2_status=mq2_status,
            mq135_status=mq135_status,
            overall_status=overall_status,
            mq2_ratio_to_baseline=mq2_ratio,
            mq135_ratio_to_baseline=mq135_ratio,
            mq2_trend=mq2_trend,
            mq135_trend=mq135_trend,
            smoke_cue_detected=smoke_cue,
            gas_anomaly_detected=gas_anomaly,
            baseline_calibrated=calibrated,
            qualitative_summary=summary,
            contributing_factors=factors,
        )

    def evaluate_telemetry(self, telemetry: Dict[str, Any], device_id: Optional[str] = None) -> GasAnomalyAssessment:
        """
        Convenience method to evaluate raw telemetry dictionary from backend/hardware.
        """
        dev_id = device_id or telemetry.get("device_id", "default_node")
        mq2_raw = float(telemetry.get("mq2_raw", 0.0))
        mq2_volt = float(telemetry.get("mq2_adc_voltage", telemetry.get("mq2_voltage", 0.0)))
        mq135_raw = float(telemetry.get("mq135_raw", 0.0))
        mq135_volt = float(telemetry.get("mq135_adc_voltage", telemetry.get("mq135_voltage", 0.0)))
        timestamp = telemetry.get("timestamp")

        return self.update(
            device_id=dev_id,
            mq2_raw=mq2_raw,
            mq2_voltage=mq2_volt,
            mq135_raw=mq135_raw,
            mq135_voltage=mq135_volt,
            timestamp=timestamp,
        )

    def cross_validate_acoustic_event(
        self,
        acoustic_class: str,
        acoustic_confidence: float,
        gas_assessment: GasAnomalyAssessment,
    ) -> Dict[str, Any]:
        """
        Cross-validate acoustic event with gas assessment for CADIE multimodal fusion.
        """
        cls_lower = acoustic_class.lower()
        is_fire_event = any(term in cls_lower for term in ["fire", "smoke", "burn", "flame"])
        is_machinery_event = any(term in cls_lower for term in ["chainsaw", "drill", "vehicle", "engine"])

        corroborated = False
        fusion_confidence_delta = 0.0
        rationale = ""

        if is_fire_event:
            if gas_assessment.smoke_cue_detected or gas_assessment.overall_status in ("ELEVATED", "CRITICAL"):
                corroborated = True
                fusion_confidence_delta = 0.15
                rationale = "Acoustic fire signature corroborated by elevated atmospheric smoke/gas telemetry."
            elif gas_assessment.overall_status == "NOMINAL" and acoustic_confidence < 0.70:
                fusion_confidence_delta = -0.10
                rationale = "Acoustic fire alert uncorroborated by clean atmospheric gas baseline."
            else:
                rationale = "Acoustic fire detected; atmospheric baseline stable."
        elif is_machinery_event and gas_assessment.overall_status in ("ELEVATED", "CRITICAL"):
            corroborated = True
            fusion_confidence_delta = 0.05
            rationale = "Machinery acoustic event accompanied by elevated exhaust/hydrocarbon anomaly."
        elif gas_assessment.overall_status in ("ELEVATED", "CRITICAL") and not is_fire_event:
            rationale = "Independent gas/smoke anomaly detected without acoustic combustion footprint."
        else:
            rationale = "Acoustic and atmospheric signals nominal."

        return {
            "corroborated": corroborated,
            "fusion_confidence_delta": fusion_confidence_delta,
            "is_fire_event": is_fire_event,
            "gas_risk_score": gas_assessment.gas_risk_score,
            "overall_gas_status": gas_assessment.overall_status,
            "rationale": rationale,
        }

    def _classify_status(self, ratio: float) -> str:
        if ratio >= self.critical_threshold:
            return "CRITICAL"
        elif ratio >= self.elevated_threshold:
            return "ELEVATED"
        elif ratio >= self.advisory_threshold:
            return "ADVISORY"
        return "NOMINAL"

    def _classify_overall_status(self, score: float, mq2_status: str, mq135_status: str) -> str:
        if "CRITICAL" in (mq2_status, mq135_status) or score >= 0.80:
            return "CRITICAL"
        elif "ELEVATED" in (mq2_status, mq135_status) or score >= 0.45:
            return "ELEVATED"
        elif "ADVISORY" in (mq2_status, mq135_status) or score >= 0.20:
            return "ADVISORY"
        return "NOMINAL"

    def _build_summary(
        self,
        status: str,
        mq2_ratio: float,
        mq135_ratio: float,
        mq2_trend: GasTrend,
        mq135_trend: GasTrend,
        smoke_cue: bool,
    ) -> str:
        if status == "CRITICAL":
            return f"CRITICAL gas/smoke anomaly detected (MQ-2: {mq2_ratio:.1f}x baseline [{mq2_trend.value}], MQ-135: {mq135_ratio:.1f}x [{mq135_trend.value}])"
        elif status == "ELEVATED":
            return f"ELEVATED atmospheric presence (MQ-2: {mq2_ratio:.1f}x baseline [{mq2_trend.value}], MQ-135: {mq135_ratio:.1f}x [{mq135_trend.value}])"
        elif status == "ADVISORY":
            return f"ADVISORY gas deviation detected (MQ-2: {mq2_ratio:.1f}x, MQ-135: {mq135_ratio:.1f}x)"
        return "Nominal atmospheric baseline (MQ-2 and MQ-135 within normal ambient ranges)"
