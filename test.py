from inference.preprocessor import PreProcessor
from inference.predictor import Predictor

preprocessor = PreProcessor()

spectrogram = preprocessor.preprocess(
    "test_audio.wav"
)

predictor = Predictor(
    "checkpoints/best_model.pth"
)

result = predictor.predict_spectrogram(spectrogram)

print(result)