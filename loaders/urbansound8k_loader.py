"""
UrbanSound8K Dataset Loader
"""

from pathlib import Path
import pandas as pd

from loaders.base_loader import BaseDatasetLoader


class UrbanSound8KLoader(BaseDatasetLoader):

    DATASET_NAME = "UrbanSound8K"

    def __init__(self, dataset_root):

        self.dataset_root = Path(dataset_root)

        self.metadata_file = (
            self.dataset_root /
            "Extracted" /
            "UrbanSound8K" /
            "metadata" /
            "UrbanSound8K.csv"
        )

        self.audio_root = (
            self.dataset_root /
            "Extracted" /
            "UrbanSound8K" /
            "audio"
        )

    def load(self):

        df = pd.read_csv(self.metadata_file)

        records = []

        for _, row in df.iterrows():

            audio_path = (
                self.audio_root /
                f"fold{row['fold']}" /
                row["slice_file_name"]
            )

            records.append({

                "dataset": self.DATASET_NAME,

                "filepath": str(audio_path),

                "filename": row["slice_file_name"],

                "original_label": row["class"],

                "split": "train",

                "fold": int(row["fold"]),

                "metadata": {

                    "fsID": row["fsID"],

                    "start": row["start"],

                    "end": row["end"],

                    "salience": row["salience"],

                    "classID": row["classID"]

                }

            })

        return pd.DataFrame(records)