from inference.preprocessor import PreProcessor
from inference.predictor import Predictor


# --------------------------------------------------
# 1. Preprocessor
# --------------------------------------------------

preprocessor = PreProcessor()

print("\nPreprocessing Configuration")
print(
    preprocessor.get_config()
)


# --------------------------------------------------
# 2. Predictor
# --------------------------------------------------

predictor = Predictor(
    enable_unknown_discovery=True
)


# --------------------------------------------------
# 3. Test audio
# --------------------------------------------------

audio_path = (
    r"D:\user\Workspace\Major project\AuraForest\AdaptiveEdgeAI\test_audio\firework.wav"
)


# --------------------------------------------------
# 4. Audio → Spectrogram
# --------------------------------------------------

spectrogram = (
    preprocessor.preprocess(
        audio_path
    )
)

print(
    "\nSpectrogram Shape :",
    tuple(spectrogram.shape)
)


# --------------------------------------------------
# 5. Prediction
# --------------------------------------------------

result = (
    predictor.predict_spectrogram(

        spectrogram,

        top_k=5,

        audio_path=audio_path,

    )
)


# --------------------------------------------------
# 6. Prediction Result
# --------------------------------------------------

print("\n")
print("=" * 60)
print("PREDICTION")
print("=" * 60)

print(
    f"Label      : {result.label}"
)

print(
    f"Class ID   : {result.class_id}"
)

print(
    f"Confidence : {result.confidence:.4f}"
)

print(
    f"Latency    : "
    f"{result.inference_time_ms:.2f} ms"
)

print(
    "\nTop Predictions:"
)

for label, confidence in result.top_k:

    print(
        f"  {label:20s} "
        f"{confidence:.4f}"
    )


# --------------------------------------------------
# 7. Unknown Discovery
# --------------------------------------------------

discovery = (
    predictor.get_last_discovery_result()
)

print("\n")
print("=" * 60)
print("UNKNOWN SOUND DISCOVERY")
print("=" * 60)

if discovery is None:

    print(
        "Unknown discovery is disabled."
    )

else:

    print(
        "Decision :",
        discovery.decision
    )

    print(
        "Buffer Size :",
        predictor.unknown_buffer_size()
    )

    if discovery.clustering_triggered:

        print(
            "Clustering : TRIGGERED"
        )

    else:

        print(
            "Clustering : Not triggered"
        )