"""
Spectrogram Visualization
"""

import matplotlib.pyplot as plt
import librosa.display


def show_spectrogram(spec):

    plt.figure(figsize=(10, 4))

    librosa.display.specshow(

        spec,

        x_axis="time",

        y_axis="mel",

        sr=16000,

        cmap="magma"

    )

    plt.colorbar(format="%+2.0f dB")

    plt.tight_layout()

    plt.show()