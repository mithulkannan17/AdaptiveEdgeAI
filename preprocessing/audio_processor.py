import librosa

import numpy as np


class AudioProcessor:

    def normalize(self, audio):

        return librosa.util.normalize(audio)

    def trim_silence(self, audio):

        audio, _ = librosa.effects.trim(audio)

        return audio