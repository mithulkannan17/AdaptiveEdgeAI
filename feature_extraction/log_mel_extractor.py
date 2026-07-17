"""
Log-Mel Spectrogram Extractor
"""

from pathlib import Path

import librosa
import numpy as np


class LogMelExtractor:

    def __init__(

        self,

        sample_rate=16000,

        n_fft=1024,

        hop_length=512,

        n_mels=128,

        fmin=20,

        fmax=8000

    ):

        self.sample_rate = sample_rate
        self.n_fft = n_fft
        self.hop_length = hop_length
        self.n_mels = n_mels
        self.fmin = fmin
        self.fmax = fmax

    def extract(self, audio_path):

        audio_path = Path(audio_path)

        audio, _ = librosa.load(
            audio_path,
            sr=self.sample_rate,
            mono=True
        )

        mel = librosa.feature.melspectrogram(

            y=audio,

            sr=self.sample_rate,

            n_fft=self.n_fft,

            hop_length=self.hop_length,

            n_mels=self.n_mels,

            fmin=self.fmin,

            fmax=self.fmax,

            power=2.0

        )

        log_mel = librosa.power_to_db(

            mel,

            ref=np.max

        )

        return log_mel.astype(np.float32)