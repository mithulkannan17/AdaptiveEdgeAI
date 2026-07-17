import librosa 
import numpy as np

class AudioLoader:

    def __init__(self, smaple_rate=16000):

        self.smaple_rate = smaple_rate

    def load(self, file_path):

        audio, sr = librosa.load(

            file_path,

            sr=self.smaple_rate,

            mono=True
        )

        return audio, sr