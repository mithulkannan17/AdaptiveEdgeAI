"""
Unit tests for MQ-2 / MQ-135 GasSensorInterpreter and GasAnomalyAssessment.
"""

import pytest

from edge.sensors.gas_interpreter import (
    ChannelBaselineTracker,
    GasAnomalyAssessment,
    GasSensorInterpreter,
    GasTrend,
)


class TestChannelBaselineTracker:

    def test_baseline_initialization_and_update(self):
        tracker = ChannelBaselineTracker(window_size=20, warmup_samples=5)
        assert tracker.is_calibrated is False

        # Feed baseline readings around 300.0 ADC
        for i in range(10):
            ratio, trend, score = tracker.update(raw_adc=300.0 + (i % 3), voltage=0.25)

        assert tracker.is_calibrated is True
        assert tracker.baseline_adc is not None
        assert 295.0 <= tracker.baseline_adc <= 305.0
        assert 0.95 <= ratio <= 1.05
        assert score < 0.20
        assert trend in (GasTrend.STABLE, GasTrend.RISING)

    def test_elevated_gas_detection(self):
        tracker = ChannelBaselineTracker(window_size=20, warmup_samples=5)
        # Establish clean baseline
        for _ in range(10):
            tracker.update(raw_adc=300.0, voltage=0.25)

        # Spike to 600.0 (2x baseline)
        ratio, trend, score = tracker.update(raw_adc=600.0, voltage=0.50)
        assert ratio >= 1.9
        assert score >= 0.70

    def test_rising_fast_trend(self):
        tracker = ChannelBaselineTracker(window_size=20, trend_window_size=5, warmup_samples=5)
        for _ in range(10):
            tracker.update(raw_adc=300.0, voltage=0.25)

        # Fast successive increases
        for i in range(5):
            ratio, trend, score = tracker.update(raw_adc=300.0 + (i * 30.0), voltage=0.30)

        assert trend == GasTrend.RISING_FAST


class TestGasSensorInterpreter:

    def test_nominal_environment(self):
        interpreter = GasSensorInterpreter(warmup_samples=5)
        for _ in range(8):
            assessment = interpreter.update(
                device_id="node_01",
                mq2_raw=250.0,
                mq2_voltage=0.20,
                mq135_raw=320.0,
                mq135_voltage=0.26,
            )

        assert assessment.overall_status == "NOMINAL"
        assert assessment.mq2_status == "NOMINAL"
        assert assessment.mq135_status == "NOMINAL"
        assert assessment.smoke_cue_detected is False
        assert assessment.gas_anomaly_detected is False
        assert assessment.gas_risk_score < 0.20
        assert assessment.baseline_calibrated is True

    def test_smoke_combustion_anomaly(self):
        interpreter = GasSensorInterpreter(warmup_samples=5)
        # Baseline
        for _ in range(8):
            interpreter.update(
                device_id="node_01",
                mq2_raw=200.0,
                mq2_voltage=0.16,
                mq135_raw=250.0,
                mq135_voltage=0.20,
            )

        # Heavy smoke anomaly on MQ-2
        assessment = interpreter.update(
            device_id="node_01",
            mq2_raw=550.0,
            mq2_voltage=0.44,
            mq135_raw=480.0,
            mq135_voltage=0.38,
        )

        assert assessment.overall_status in ("ELEVATED", "CRITICAL")
        assert assessment.mq2_status in ("ELEVATED", "CRITICAL")
        assert assessment.smoke_cue_detected is True
        assert assessment.gas_anomaly_detected is True
        assert assessment.gas_risk_score >= 0.50

    def test_evaluate_telemetry_dict(self):
        interpreter = GasSensorInterpreter(warmup_samples=3)
        telemetry = {
            "device_id": "esp32_forest_01",
            "mq2_raw": 300.0,
            "mq2_adc_voltage": 0.24,
            "mq135_raw": 350.0,
            "mq135_adc_voltage": 0.28,
        }
        for _ in range(5):
            assessment = interpreter.evaluate_telemetry(telemetry)

        assert isinstance(assessment, GasAnomalyAssessment)
        assert assessment.to_dict()["baseline_calibrated"] is True

    def test_multimodal_cross_validation(self):
        interpreter = GasSensorInterpreter(warmup_samples=5)
        # Establish baseline
        for _ in range(8):
            interpreter.update("node_01", mq2_raw=200.0, mq2_voltage=0.16, mq135_raw=200.0, mq135_voltage=0.16)

        # 1. Clean air + acoustic chainsaw -> no false fire boost
        nom_assessment = interpreter.update("node_01", mq2_raw=205.0, mq2_voltage=0.16, mq135_raw=205.0, mq135_voltage=0.16)
        res1 = interpreter.cross_validate_acoustic_event("Chainsaw", 0.95, nom_assessment)
        assert res1["corroborated"] is False

        # 2. Elevated smoke + acoustic fire -> corroborated boost
        smoke_assessment = interpreter.update("node_01", mq2_raw=600.0, mq2_voltage=0.48, mq135_raw=500.0, mq135_voltage=0.40)
        res2 = interpreter.cross_validate_acoustic_event("Fire", 0.85, smoke_assessment)
        assert res2["corroborated"] is True
        assert res2["fusion_confidence_delta"] > 0
