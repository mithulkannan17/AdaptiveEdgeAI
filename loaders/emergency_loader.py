"""
Emergency Dataset Loader
"""

from pathlib import Path
import pandas as pd

from loaders.base_loader import BaseDatasetLoader


class EmergencyLoader(BaseDatasetLoader):

    DATASET_NAME = "Emergency"

    def __init__(self, dataset_root):

        self.dataset_root = Path(dataset_root)

        self.metadata_file = (
            self.dataset_root /
            "Metadata" /
            "emergency_metadata.csv"
        )

        self.audio_root = (
            self.dataset_root /
            "Extracted"
        )

    def load(self):

        df = pd.read_csv(self.metadata_file)

        records = []

        for _, row in df.iterrows():

            records.append({

                "dataset": self.DATASET_NAME,

                "filepath": str(
                    self.audio_root /
                    row["audio_folder"] /
                    row["filename"]
                ),

                "filename": row["filename"],

                "original_label": row["label"],

                "split": "train",

                "fold": None,

                "metadata": {}

            })

        return pd.DataFrame(records)