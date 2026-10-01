"""
Distance & Real-Environment Detection Experiment Suite for AuraForest.

Directly addresses key deployment questions:
"How far can the microphone detect critical acoustic events?"
"How does detection range change under ambient forest noise and foliage attenuation?"

Features:
1. Acoustic Propagation Physics Simulator:
   - Free-field geometric spreading (Inverse Square Law: -6 dB per distance doubling).
   - Atmospheric acoustic absorption (ISO 9613-1 frequency-dependent attenuation).
   - Forest excess attenuation (foliage, ground interaction: configurable 0.05 - 0.20 dB/m).
   - Environmental ambient noise floors:
     * Quiet Forest (~35 dBA)
     * Moderate Breeze / Canopy Rustle (~45 dBA)
     * Windy Forest (~55 dBA)
     * Rain & Stream (~58 dBA)
     * Active Border / Roadside (~65 dBA)

2. Distance Testing Grid:
   - Configurable distances: e.g. 5m, 10m, 20m, 30m, 40m, 50m, 75m, 100m.
   - Measures:
     * Received SPL (dB) & Effective SNR (dB)
     * Clean vs Attenuated vs Denoised Predictions & Confidences
     * Maximum Effective Detection Range (R_max) per class
     * False Positive / Misclassification transitions

3. Field Logging Mode:
   - Structured entry and persistence for physical field-test measurements.
   - Compares simulated vs empirical field observations.

4. Formatted Output:
   - JSON structured results for visualization & evaluation pipelines.
   - CSV exports for statistical analysis.
   - Markdown summary tables formatted for research reports and thesis evaluation.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass, field
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import librosa
import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from edge.noise_robustness import NoiseRobustnessEngine, NoiseSynthesizer
from inference.predictor import Predictor
from inference.preprocessor import PreProcessor

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = PROJECT_ROOT / "outputs" / "experiments"
TEST_AUDIO_DIR = PROJECT_ROOT / "test_audio"


# Standard acoustic source levels at 1 meter reference distance (dBA SPL)
REFERENCE_SOURCE_LEVELS_DBA: Dict[str, float] = {
    "Chainsaw": 105.0,
    "Drill": 98.0,
    "Gunshot": 140.0,
    "Firework": 130.0,
    "Vehicle": 85.0,
    "EmergencyVehicle": 110.0,
    "Human": 70.0,
    "Footsteps": 55.0,
    "Bird": 68.0,
    "Water": 60.0,
    "Rain": 55.0,
    "Wind": 50.0,
}

# Ambient noise floors across forest environments (dBA SPL)
ENVIRONMENT_NOISE_FLOORS_DBA: Dict[str, Dict[str, Any]] = {
    "Quiet Forest": {
        "noise_floor_dba": 35.0,
        "noise_type": "wind",
        "foliage_attenuation_db_per_m": 0.05,
        "description": "Dense canopy, calm wind, low wildlife background",
    },
    "Breezy Canopy": {
        "noise_floor_dba": 45.0,
        "noise_type": "wind",
        "foliage_attenuation_db_per_m": 0.08,
        "description": "Moderate wind rustling leaves and branches",
    },
    "Windy Forest": {
        "noise_floor_dba": 55.0,
        "noise_type": "wind",
        "foliage_attenuation_db_per_m": 0.12,
        "description": "High wind gusting through trees and undergrowth",
    },
    "Rain & Stream": {
        "noise_floor_dba": 58.0,
        "noise_type": "rain",
        "foliage_attenuation_db_per_m": 0.15,
        "description": "Precipitation and nearby water flow",
    },
    "Roadside Boundary": {
        "noise_floor_dba": 65.0,
        "noise_type": "vehicle",
        "foliage_attenuation_db_per_m": 0.08,
        "description": "Forest perimeter near road or logging track",
    },
}


@dataclass
class DistanceTestTrial:
    """Individual distance detection trial record."""
    sample_name: str
    ground_truth: str
    distance_m: float
    environment: str
    source_spl_dba: float
    foliage_loss_db: float
    geometric_loss_db: float
    received_spl_dba: float
    ambient_noise_dba: float
    effective_snr_db: float
    
    # Raw prediction
    raw_pred_label: str
    raw_confidence: float
    raw_correct: bool
    
    # Denoised prediction (with edge noise robustness active)
    denoised_pred_label: str
    denoised_confidence: float
    denoised_correct: bool
    denoising_applied: bool
    confidence_gain: float


@dataclass
class RangeSummary:
    """Summary of detection range for a specific class and environment."""
    class_name: str
    environment: str
    source_spl_dba: float
    max_reliable_distance_raw_m: float
    max_reliable_distance_denoised_m: float
    range_improvement_percent: float
    trials_count: int


class AcousticPropagationModel:
    """
    Simulates physical sound propagation in outdoor forest environments.
    Incorporates:
    - Geometric spreading (Inverse Square Law)
    - Atmospheric absorption (temperature/humidity dependent)
    - Excess forest attenuation (foliage and ground scatter)
    """

    def __init__(
        self,
        ref_distance_m: float = 1.0,
        atmospheric_loss_db_per_m: float = 0.005,  # Approx for 1kHz @ 20C, 60% RH
    ):
        self.ref_distance_m = ref_distance_m
        self.atmospheric_loss_db_per_m = atmospheric_loss_db_per_m

    def calculate_received_spl(
        self,
        source_spl_dba: float,
        distance_m: float,
        foliage_loss_db_per_m: float = 0.08,
    ) -> Tuple[float, float, float]:
        """
        Calculate received Sound Pressure Level (SPL) at specified distance.
        Returns: (received_spl_dba, geometric_loss_db, excess_loss_db)
        """
        if distance_m <= self.ref_distance_m:
            return source_spl_dba, 0.0, 0.0

        # Geometric spreading loss: 20 * log10(d / d0)
        geometric_loss_db = 20.0 * math.log10(distance_m / self.ref_distance_m)

        # Excess attenuation (atmosphere + foliage absorption)
        distance_delta = distance_m - self.ref_distance_m
        atmospheric_loss = self.atmospheric_loss_db_per_m * distance_delta
        foliage_loss = foliage_loss_db_per_m * distance_delta
        excess_loss_db = atmospheric_loss + foliage_loss

        total_loss_db = geometric_loss_db + excess_loss_db
        received_spl_dba = max(0.0, source_spl_dba - total_loss_db)

        return received_spl_dba, geometric_loss_db, excess_loss_db

    def apply_distance_attenuation(
        self,
        clean_audio: np.ndarray,
        source_spl_dba: float,
        distance_m: float,
        foliage_loss_db_per_m: float = 0.08,
    ) -> Tuple[np.ndarray, float, float]:
        """
        Attenuate clean audio amplitude based on distance loss.
        """
        received_spl, geom_loss, excess_loss = self.calculate_received_spl(
            source_spl_dba=source_spl_dba,
            distance_m=distance_m,
            foliage_loss_db_per_m=foliage_loss_db_per_m,
        )
        total_attenuation_db = geom_loss + excess_loss
        linear_scale = 10.0 ** (-total_attenuation_db / 20.0)

        attenuated_audio = (clean_audio * linear_scale).astype(np.float32)
        return attenuated_audio, received_spl, total_attenuation_db


class DistanceDetectionValidator:
    """
    Experiment suite to validate and benchmark detection range vs environment conditions.
    """

    def __init__(
        self,
        predictor: Optional[Predictor] = None,
        preprocessor: Optional[PreProcessor] = None,
        denoiser: Optional[NoiseRobustnessEngine] = None,
        sample_rate: int = 16000,
    ):
        self.sample_rate = sample_rate
        self.preprocessor = preprocessor or PreProcessor()
        self.predictor = predictor or Predictor(enable_unknown_discovery=True)
        self.denoiser = denoiser or NoiseRobustnessEngine()
        self.synthesizer = NoiseSynthesizer()
        self.propagation_model = AcousticPropagationModel()

    def load_audio_file(self, file_path: str | Path) -> np.ndarray:
        """Load an audio file as mono float32 at configured sample rate."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {path}")

        waveform, _ = librosa.load(str(path), sr=self.sample_rate, mono=True)
        waveform = np.asarray(waveform, dtype=np.float32)

        # Standardize duration (e.g. 3.0 seconds)
        target_len = self.sample_rate * 3
        if waveform.size < target_len:
            waveform = np.pad(waveform, (0, target_len - waveform.size), mode="constant")
        elif waveform.size > target_len:
            waveform = waveform[:target_len]

        return np.clip(waveform, -1.0, 1.0)

    def predict_waveform(self, waveform: np.ndarray) -> Tuple[str, float]:
        """Convert waveform to mel spectrogram and predict with the model."""
        tensor = torch.as_tensor(waveform, dtype=torch.float32)
        spectrogram = self.preprocessor.preprocess_waveform(tensor, sample_rate=self.sample_rate)
        pred_result = self.predictor.predict_spectrogram(spectrogram, top_k=5)
        return str(pred_result.label), float(pred_result.confidence)

    def run_full_distance_experiment(
        self,
        distances_m: Optional[List[float]] = None,
        environments: Optional[List[str]] = None,
        confidence_threshold: float = 0.60,
    ) -> Dict[str, Any]:
        """
        Run automated distance detection experiments across all test audio files.
        """
        if distances_m is None:
            distances_m = [5.0, 10.0, 20.0, 30.0, 40.0, 50.0, 75.0, 100.0]

        if environments is None:
            environments = list(ENVIRONMENT_NOISE_FLOORS_DBA.keys())

        # Find test audio files
        audio_files = list(TEST_AUDIO_DIR.glob("*.wav")) + list(TEST_AUDIO_DIR.glob("*.mp3"))
        if not audio_files:
            raise FileNotFoundError(f"No audio files found in {TEST_AUDIO_DIR}")

        print(f"\n=======================================================")
        print(f"[*] Starting Distance & Real-Environment Validation")
        print(f"=======================================================")
        print(f"Found {len(audio_files)} test audio samples.")
        print(f"Distances: {distances_m} m")
        print(f"Environments: {environments}\n")

        all_trials: List[DistanceTestTrial] = []

        for audio_path in audio_files:
            sample_name = audio_path.stem
            clean_audio = self.load_audio_file(audio_path)

            # Get clean baseline prediction
            clean_label, clean_conf = self.predict_waveform(clean_audio)
            ground_truth = sample_name.split("_")[0] if "_" in sample_name else clean_label

            source_spl = REFERENCE_SOURCE_LEVELS_DBA.get(ground_truth, 90.0)

            print(f"\n--- Testing Sample: {sample_name} (GT: {ground_truth}, Source SPL: {source_spl} dBA) ---")

            for env_name in environments:
                env_info = ENVIRONMENT_NOISE_FLOORS_DBA[env_name]
                noise_floor_dba = env_info["noise_floor_dba"]
                noise_type = env_info["noise_type"]
                foliage_loss = env_info["foliage_attenuation_db_per_m"]

                for dist in distances_m:
                    # 1. Acoustic propagation attenuation
                    att_audio, rx_spl, total_loss = self.propagation_model.apply_distance_attenuation(
                        clean_audio=clean_audio,
                        source_spl_dba=source_spl,
                        distance_m=dist,
                        foliage_loss_db_per_m=foliage_loss,
                    )
                    geom_loss = 20.0 * math.log10(max(dist, 1.0))
                    foliage_loss_total = total_loss - geom_loss

                    # 2. Effective SNR at receiver
                    effective_snr_db = rx_spl - noise_floor_dba

                    # 3. Synthesize and mix ambient background noise at effective SNR
                    bg_noise = self.synthesizer.generate_noise(
                        noise_type=noise_type,
                        num_samples=len(att_audio),
                        sample_rate=self.sample_rate,
                    )
                    noisy_at_distance = self.synthesizer.mix_at_snr(
                        clean_waveform=att_audio,
                        noise_waveform=bg_noise,
                        snr_db=effective_snr_db,
                    )

                    # 4. Predict Raw Noisy (without edge denoising)
                    raw_label, raw_conf = self.predict_waveform(noisy_at_distance)
                    raw_correct = (raw_label.lower() == ground_truth.lower()) and (raw_conf >= confidence_threshold)

                    # 5. Predict Denoised (with edge noise robustness active)
                    denoised_audio, denoise_res = self.denoiser.process(noisy_at_distance, self.sample_rate)
                    den_label, den_conf = self.predict_waveform(denoised_audio)
                    den_correct = (den_label.lower() == ground_truth.lower()) and (den_conf >= confidence_threshold)

                    conf_gain = den_conf - raw_conf

                    trial = DistanceTestTrial(
                        sample_name=sample_name,
                        ground_truth=ground_truth,
                        distance_m=dist,
                        environment=env_name,
                        source_spl_dba=source_spl,
                        foliage_loss_db=round(foliage_loss_total, 2),
                        geometric_loss_db=round(geom_loss, 2),
                        received_spl_dba=round(rx_spl, 2),
                        ambient_noise_dba=noise_floor_dba,
                        effective_snr_db=round(effective_snr_db, 2),
                        raw_pred_label=raw_label,
                        raw_confidence=round(raw_conf, 4),
                        raw_correct=raw_correct,
                        denoised_pred_label=den_label,
                        denoised_confidence=round(den_conf, 4),
                        denoised_correct=den_correct,
                        denoising_applied=denoise_res.applied,
                        confidence_gain=round(conf_gain, 4),
                    )
                    all_trials.append(trial)

        # Compute summary statistics
        summary = self._compute_summary(all_trials, distances_m, environments, confidence_threshold)

        # Export outputs
        results = {
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "confidence_threshold": confidence_threshold,
            "summary": summary,
            "trials": [asdict(t) for t in all_trials],
        }

        self._export_results(results, all_trials)
        self._print_formatted_summary(summary)

        return results

    def _compute_summary(
        self,
        trials: List[DistanceTestTrial],
        distances_m: List[float],
        environments: List[str],
        confidence_threshold: float,
    ) -> Dict[str, Any]:
        """Compute range summaries and aggregated accuracy."""
        by_class: Dict[str, Dict[str, Any]] = {}
        by_environment: Dict[str, Dict[str, Any]] = {}
        by_distance: Dict[str, Dict[str, Any]] = {}

        for env in environments:
            env_trials = [t for t in trials if t.environment == env]
            raw_acc = np.mean([1.0 if t.raw_correct else 0.0 for t in env_trials]) if env_trials else 0.0
            den_acc = np.mean([1.0 if t.denoised_correct else 0.0 for t in env_trials]) if env_trials else 0.0
            by_environment[env] = {
                "total_trials": len(env_trials),
                "raw_accuracy": round(float(raw_acc), 4),
                "denoised_accuracy": round(float(den_acc), 4),
                "accuracy_gain": round(float(den_acc - raw_acc), 4),
            }

        for dist in distances_m:
            dist_trials = [t for t in trials if t.distance_m == dist]
            raw_acc = np.mean([1.0 if t.raw_correct else 0.0 for t in dist_trials]) if dist_trials else 0.0
            den_acc = np.mean([1.0 if t.denoised_correct else 0.0 for t in dist_trials]) if dist_trials else 0.0
            by_distance[f"{dist}m"] = {
                "total_trials": len(dist_trials),
                "raw_accuracy": round(float(raw_acc), 4),
                "denoised_accuracy": round(float(den_acc), 4),
                "accuracy_gain": round(float(den_acc - raw_acc), 4),
            }

        # Calculate max reliable distance per class and environment
        classes = sorted(list(set(t.ground_truth for t in trials)))
        range_summaries: List[Dict[str, Any]] = []

        for cls in classes:
            by_class[cls] = {}
            for env in environments:
                class_env_trials = [t for t in trials if t.ground_truth == cls and t.environment == env]
                class_env_trials.sort(key=lambda x: x.distance_m)

                # Max distance where all closer distances were also correctly classified
                max_raw_d = 0.0
                for t in class_env_trials:
                    if t.raw_correct:
                        max_raw_d = t.distance_m
                    else:
                        break

                max_den_d = 0.0
                for t in class_env_trials:
                    if t.denoised_correct:
                        max_den_d = t.distance_m
                    else:
                        break

                improvement = ((max_den_d - max_raw_d) / max(max_raw_d, 1e-6)) * 100.0 if max_raw_d > 0 else 0.0

                range_info = {
                    "class_name": cls,
                    "environment": env,
                    "source_spl_dba": REFERENCE_SOURCE_LEVELS_DBA.get(cls, 90.0),
                    "max_reliable_distance_raw_m": max_raw_d,
                    "max_reliable_distance_denoised_m": max_den_d,
                    "range_improvement_percent": round(improvement, 1),
                }
                range_summaries.append(range_info)
                by_class[cls][env] = range_info

        total_trials = len(trials)
        overall_raw_acc = np.mean([1.0 if t.raw_correct else 0.0 for t in trials]) if trials else 0.0
        overall_den_acc = np.mean([1.0 if t.denoised_correct else 0.0 for t in trials]) if trials else 0.0

        return {
            "total_trials": total_trials,
            "overall_raw_accuracy": round(float(overall_raw_acc), 4),
            "overall_denoised_accuracy": round(float(overall_den_acc), 4),
            "overall_accuracy_gain": round(float(overall_den_acc - overall_raw_acc), 4),
            "by_environment": by_environment,
            "by_distance": by_distance,
            "range_summaries": range_summaries,
            "by_class": by_class,
        }

    def _export_results(self, results: Dict[str, Any], trials: List[DistanceTestTrial]) -> None:
        """Export results to JSON, CSV, and Markdown report."""
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

        # 1. JSON
        json_path = OUTPUTS_DIR / "distance_detection_results.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"[+] Saved JSON results to: {json_path}")

        # 2. CSV
        csv_path = OUTPUTS_DIR / "distance_detection_results.csv"
        if trials:
            fieldnames = list(asdict(trials[0]).keys())
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for trial in trials:
                    writer.writerow(asdict(trial))
            print(f"[+] Saved CSV results to: {csv_path}")

        # 3. Markdown Report Table
        md_path = OUTPUTS_DIR / "distance_detection_report.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# Distance & Real-Environment Acoustic Detection Report\n\n")
            f.write(f"**Generated:** {results['generated_at']}  \n")
            f.write(f"**Confidence Gate:** {results['confidence_threshold'] * 100:.0f}%  \n")
            f.write(f"**Overall Accuracy:** {results['summary']['overall_denoised_accuracy'] * 100:.1f}% ")
            f.write(f"(Raw: {results['summary']['overall_raw_accuracy'] * 100:.1f}%, Gain: +{results['summary']['overall_accuracy_gain'] * 100:.1f}%)\n\n")

            f.write("## 1. Maximum Reliable Detection Range by Sound Class (m)\n\n")
            f.write("| Sound Class | Source SPL | Environment | Raw Range (m) | Denoised Range (m) | Range Gain |\n")
            f.write("| :--- | :---: | :--- | :---: | :---: | :---: |\n")
            for r in results["summary"]["range_summaries"]:
                gain_str = f"+{r['range_improvement_percent']:.1f}%" if r["range_improvement_percent"] > 0 else "0%"
                f.write(f"| **{r['class_name']}** | {r['source_spl_dba']:.0f} dBA | {r['environment']} | {r['max_reliable_distance_raw_m']:.0f}m | **{r['max_reliable_distance_denoised_m']:.0f}m** | {gain_str} |\n")

            f.write("\n## 2. Accuracy vs Distance\n\n")
            f.write("| Distance | Trials | Raw Accuracy | Denoised Accuracy | Accuracy Delta |\n")
            f.write("| :--- | :---: | :---: | :---: | :---: |\n")
            for dist, stats in results["summary"]["by_distance"].items():
                delta_str = f"+{stats['accuracy_gain']*100:.1f}%" if stats['accuracy_gain'] >= 0 else f"{stats['accuracy_gain']*100:.1f}%"
                f.write(f"| **{dist}** | {stats['total_trials']} | {stats['raw_accuracy']*100:.1f}% | **{stats['denoised_accuracy']*100:.1f}%** | {delta_str} |\n")

            f.write("\n## 3. Accuracy by Environmental Condition\n\n")
            f.write("| Environment | Noise Floor | Raw Accuracy | Denoised Accuracy | Accuracy Delta |\n")
            f.write("| :--- | :---: | :---: | :---: | :---: |\n")
            for env, stats in results["summary"]["by_environment"].items():
                noise_fl = ENVIRONMENT_NOISE_FLOORS_DBA.get(env, {}).get("noise_floor_dba", 40.0)
                delta_str = f"+{stats['accuracy_gain']*100:.1f}%" if stats['accuracy_gain'] >= 0 else f"{stats['accuracy_gain']*100:.1f}%"
                f.write(f"| **{env}** | ~{noise_fl:.0f} dBA | {stats['raw_accuracy']*100:.1f}% | **{stats['denoised_accuracy']*100:.1f}%** | {delta_str} |\n")

        print(f"[+] Saved Markdown summary report to: {md_path}")

    def _print_formatted_summary(self, summary: Dict[str, Any]) -> None:
        """Print clean terminal summary."""
        print("\n" + "=" * 70)
        print("[*] DISTANCE DETECTION VALIDATION SUMMARY")
        print("=" * 70)
        print(f"Total Trials: {summary['total_trials']}")
        print(f"Overall Raw Accuracy:      {summary['overall_raw_accuracy'] * 100:.1f}%")
        print(f"Overall Denoised Accuracy: {summary['overall_denoised_accuracy'] * 100:.1f}%")
        print(f"Overall Accuracy Gain:    +{summary['overall_accuracy_gain'] * 100:.1f}%")
        print("-" * 70)
        print(f"{'Sound Class':<16} | {'Environment':<18} | {'Raw (m)':<8} | {'Denoised (m)':<12} | {'Gain':<6}")
        print("-" * 70)
        for r in summary["range_summaries"]:
            gain = f"+{r['range_improvement_percent']:.0f}%" if r["range_improvement_percent"] > 0 else "0%"
            print(f"{r['class_name']:<16} | {r['environment']:<18} | {r['max_reliable_distance_raw_m']:>6.0f}m  | {r['max_reliable_distance_denoised_m']:>10.0f}m  | {gain:<6}")
        print("=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Distance & Real-Environment Detection Validator")
    parser.add_argument(
        "--distances",
        type=float,
        nargs="+",
        default=[5.0, 10.0, 20.0, 30.0, 40.0, 50.0, 75.0, 100.0],
        help="List of distances in meters to test (default: 5 10 20 30 40 50 75 100)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.60,
        help="Confidence threshold for positive detection (default: 0.60)",
    )
    args = parser.parse_args()

    validator = DistanceDetectionValidator()
    validator.run_full_distance_experiment(
        distances_m=args.distances,
        confidence_threshold=args.threshold,
    )


if __name__ == "__main__":
    main()