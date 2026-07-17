import pandas as pd

from pathlib import Path

from .base_loader import BaseDatasetLoader


class UrbanSoundLoader(BaseDatasetLoader):

    def load_metadata(self):

        metadata = self.dataset_path / "meta" / "UrbanSound8K.csv"

        return pd.read_csv(metadata)

    def dataset_info(self):

        df = self.load_metadata()

        return {

            "Dataset": "UrbanSound8K",

            "Samples": len(df),

            "Classes": df["category"].nunique()
        }