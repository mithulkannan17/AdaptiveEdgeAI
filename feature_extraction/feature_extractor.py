from .mel_spectrogram import MelSpectrogram


class FeatureExtractor:

    def __init__(self):

        self.mel = MelSpectrogram()

    def extract(self, audio):

        return self.mel.generate(audio)