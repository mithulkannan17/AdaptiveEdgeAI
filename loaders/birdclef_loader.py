"""
BirdCLEF 2026 Dataset Loader
"""

from pathlib import Path

import pandas as pd

from loaders.base_loader import BaseDatasetLoader


class BirdCLEFLoader(BaseDatasetLoader):

    DATASET_NAME = "BirdCLEF2026"

    def __init__(self, dataset_root):

        self.dataset_root = Path(dataset_root)

        self.metadata_file = (
            self.dataset_root /
            "train.csv"
        )

        self.audio_folder = (
            self.dataset_root /
            "train_audio"
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

                "filename": Path(
                    row["filename"]
                ).name,

                "original_label": row["class_name"],

                "split": "train",

                "fold": None,

                "metadata": {

                    "primary_label": row["primary_label"],

                    "scientific_name": row["scientific_name"],

                    "common_name": row["common_name"],

                    "class_name": row["class_name"],

                    "latitude": row["latitude"],

                    "longitude": row["longitude"],

                    "rating": row["rating"],

                    "collection": row["collection"]

                }

            })

        return pd.DataFrame(records)