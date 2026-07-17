import os
import soundfile as sf


class AudioSplitter:

    def __init__(self, sample_rate=16000, clip_duration=5):

        self.sample_rate = sample_rate
        self.clip_samples = sample_rate * clip_duration

    def split(self, audio, output_folder, base_name):

        os.makedirs(output_folder, exist_ok=True)

        total = len(audio)

        count = 1

        for start in range(0, total, self.clip_samples):

            end = start + self.clip_samples

            clip = audio[start:end]

            if len(clip) < self.clip_samples:
                continue

            filename = f"{base_name}_{count:04d}.wav"

            sf.write(
                os.path.join(output_folder, filename),
                clip,
                self.sample_rate
            )

            count += 1