"""
FSD50K Dataset Loader
"""

from pathlib import Path
import pandas as pd

from loaders.base_loader import BaseDatasetLoader


class FSD50KLoader(BaseDatasetLoader):

    DATASET_NAME = "FSD50K"

    def __init__(self, dataset_root):

        self.dataset_root = Path(dataset_root)

        self.metadata_file = (
            self.dataset_root /
            "Metadata" /
            "dev.csv"
        )

        self.audio_root = (
            self.dataset_root /
            "Extracted" /
            "FSD50K.dev_audio"
        )

    def load(self):

        df = pd.read_csv(self.metadata_file)

        records = []

        for _, row in df.iterrows():

            audio_path = (
                self.audio_root /
                f"{row['fname']}.wav"
            )

            labels = str(row["labels"]).split(",")

            records.append({

                "dataset": self.DATASET_NAME,

                "filepath": str(audio_path),

                "filename": f"{row['fname']}.wav",

                "original_label": labels,

                "split": row["split"],

                "fold": None,

                "metadata": {

                    "mids": row["mids"]

                }

            })

        return pd.DataFrame(records)