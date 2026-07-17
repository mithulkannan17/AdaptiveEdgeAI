import librosa
import librosa.display
import numpy as np


class MelSpectrogram:

    def __init__(self):

        self.sample_rate = 16000

        self.n_fft = 1024

        self.hop_length = 512

        self.n_mels = 128

    def generate(self, audio):

        mel = librosa.feature.melspectrogram(

            y=audio,

            sr=self.sample_rate,

            n_fft=self.n_fft,

            hop_length=self.hop_length,

            n_mels=self.n_mels

        )

        mel_db = librosa.power_to_db(mel)

        return mel_db