"""
Real End-to-End Edge Pipeline Test

Runs an actual audio file through:

Audio
    ↓
PreProcessor
    ↓
MobileNetV3-Small
    ↓
Unknown Discovery
    ↓
Environmental Profiling
    ↓
Adaptive Behaviour
    ↓
Event Detection
    ↓
Event Prioritization
    ↓
EdgeRuntimeResult
    ↓
EdgeMessageSerializer
    ↓
FastAPI
    ↓
SQLite
"""

from pathlib import Path

from inference.preprocessor import PreProcessor
from inference.predictor import Predictor

from edge.runtime.edge_controller import (
    EdgeController,
)

from communication import (
    EdgeRuntimeService,
)


# --------------------------------------------------
# CHANGE THIS PATH
# --------------------------------------------------

AUDIO_FILE = Path(
    r"D:\user\Workspace\Major project\AuraForest\AdaptiveEdgeAI\test_audio\chainsaw.mp3"
)


def main():

    print()
    print("=" * 60)
    print("REAL EDGE-TO-BACKEND INTEGRATION TEST")
    print("=" * 60)

    # --------------------------------------------------
    # Validate audio
    # --------------------------------------------------

    if not AUDIO_FILE.exists():

        raise FileNotFoundError(
            f"Audio file not found: {AUDIO_FILE}"
        )

    # --------------------------------------------------
    # Preprocessor
    # --------------------------------------------------

    preprocessor = PreProcessor()

    print()
    print("Preprocessing audio...")

    spectrogram = (
        preprocessor.preprocess(
            AUDIO_FILE
        )
    )

    print(
        f"Spectrogram Shape : "
        f"{tuple(spectrogram.shape)}"
    )

    # --------------------------------------------------
    # Predictor
    # --------------------------------------------------

    print()
    print("Loading production predictor...")

    predictor = Predictor(
        enable_unknown_discovery=True
    )

    # --------------------------------------------------
    # Edge Controller
    # --------------------------------------------------

    controller = EdgeController(
        predictor=predictor
    )

    # --------------------------------------------------
    # Communication Service
    # --------------------------------------------------

    service = EdgeRuntimeService(

        controller=controller,

        device_id="edge_node_001",

    )

    # --------------------------------------------------
    # Execute complete pipeline
    # --------------------------------------------------

    print()
    print("Running complete edge pipeline...")

    response = service.process_spectrogram(

        spectrogram=spectrogram,

        top_k=5,

        audio_path=AUDIO_FILE,

        location=None,

        device_status={

            "battery_percent":
                None,

            "temperature":
                None,

            "humidity":
                None,

        },

    )

    # --------------------------------------------------
    # Runtime result
    # --------------------------------------------------

    runtime_result = (
        service.get_last_runtime_result()
    )

    print()
    print("=" * 60)
    print("EDGE RUNTIME RESULT")
    print("=" * 60)

    print(
        f"Prediction : "
        f"{runtime_result.prediction.label}"
    )

    print(
        f"Confidence : "
        f"{runtime_result.prediction.confidence:.4f}"
    )

    print(
        f"Environment : "
        f"{runtime_result.environment_profile.environment_type}"
    )

    print(
        f"Threshold : "
        f"{runtime_result.adaptive_policy.detection_threshold}"
    )

    print(
        f"Event : "
        f"{runtime_result.event.label}"
    )

    print(
        f"Detected : "
        f"{runtime_result.event.detected}"
    )

    print(
        f"Priority : "
        f"{runtime_result.event.priority}"
    )

    # --------------------------------------------------
    # Backend response
    # --------------------------------------------------

    print()
    print("=" * 60)
    print("BACKEND RESPONSE")
    print("=" * 60)

    print(response)

    # --------------------------------------------------
    # Communication message
    # --------------------------------------------------

    message = (
        service.get_last_message()
    )

    print()
    print("=" * 60)
    print("COMMUNICATION MESSAGE")
    print("=" * 60)

    print(
        message.to_dict()
    )

    print()
    print("=" * 60)
    print("END-TO-END TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":

    main()