from inference.predictor import Predictor

predictor = Predictor(
    checkpoint_path="models/checkpoints/best_model.pth"
)

result = predictor.predict_spectrogram(spectrogram)

print(result)
print(result.label)
print(result.confidence)