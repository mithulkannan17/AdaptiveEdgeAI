from pathlib import Path

import librosa


class AudioValidator:

    @staticmethod
    def validate(file_path):

        file_path = Path(file_path)

        if not file_path.exists():

            return False

        try:

            duration = librosa.get_duration(path=file_path)

            if duration < 0.5:

                return False

        except Exception:

            return False

        return True