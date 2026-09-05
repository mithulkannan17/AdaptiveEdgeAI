
import torch

from inference.predictor import Predictor
from inference.preprocessor import PreProcessor


p = Predictor()
pp = PreProcessor()

waveform = torch.randn(80000)
spectrogram = pp.preprocess_waveform(
    waveform,
    16000
)

values = [
    0,
    -1,
    1,
    5,
    1000,
    "5",
]

print("TOP_K ROBUSTNESS TEST")
print("=" * 60)

for value in values:

    print()
    print("TOP_K:", repr(value))

    try:

        result = p.predict_spectrogram(
            spectrogram,
            top_k=value,
        )

        print(
            "SUCCESS:",
            len(result.top_k),
            "predictions"
        )

    except Exception as e:

        print(
            "ERROR:",
            type(e).__name__,
            "-",
            e
        )
