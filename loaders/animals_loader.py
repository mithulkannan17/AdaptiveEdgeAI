"""
Animals Dataset Loader
"""

from pathlib import Path

import pandas as pd

from loaders.base_loader import BaseDatasetLoader


class AnimalsLoader(BaseDatasetLoader):

    DATASET_NAME = "Animals"

    AUDIO_EXTENSIONS = {
        ".wav",
        ".mp3",
        ".ogg",
        ".flac",
        ".m4a"
    }

    def __init__(self, dataset_root):

        self.dataset_root = Path(dataset_root)

    def load(self):

        if not self.dataset_root.exists():

            raise FileNotFoundError(
                self.dataset_root
            )

        records = []

        for class_folder in sorted(self.dataset_root.iterdir()):

            if not class_folder.is_dir():

                continue

            original_label = class_folder.name

            for audio_file in class_folder.rglob("*"):

                if (
                    audio_file.is_file()
                    and audio_file.suffix.lower()
                    in self.AUDIO_EXTENSIONS
                ):

                    records.append({

                        "dataset": self.DATASET_NAME,

                        "filepath": str(audio_file),

                        "filename": audio_file.name,

                        "original_label": original_label,

                        "split": "train",

                        "fold": None,

                        "metadata": {}

                    })

        return pd.DataFrame(records)