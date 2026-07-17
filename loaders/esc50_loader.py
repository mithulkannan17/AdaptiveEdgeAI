"""
ESC-50 Dataset Loader
"""

from pathlib import Path
import pandas as pd

from loaders.base_loader import BaseDatasetLoader


class ESC50Loader(BaseDatasetLoader):

    DATASET_NAME = "ESC50"

    def __init__(self, dataset_root):

        self.dataset_root = Path(dataset_root)

        self.metadata_file = (
            self.dataset_root /
            "meta" /
            "esc50.csv"
        )

        self.audio_folder = (
            self.dataset_root /
            "audio"
        )

    def load(self):

        if not self.metadata_file.exists():

            raise FileNotFoundError(
                self.metadata_file
            )

        df = pd.read_csv(self.metadata_file)

        records = []

        for _, row in df.iterrows():

            audio_path = (
                self.audio_folder /
                row["filename"]
            )

            records.append({

                "dataset": self.DATASET_NAME,

                "filepath": str(audio_path),

                "filename": row["filename"],

                "original_label": row["category"],

                "split": "train",

                "fold": int(row["fold"]),

                "metadata": {

                    "target": int(row["target"]),

                    "esc10": bool(row["esc10"]),

                    "src_file": row["src_file"],

                    "take": row["take"]

                }

            })

        return pd.DataFrame(records)