import pandas as pd

from pathlib import Path

from .base_loader import BaseDatasetLoader


class ESC50Loader(BaseDatasetLoader):

    def load_metadata(self):

        metadata = self.dataset_path / "meta" / "esc50.csv"

        return pd.read_csv(metadata)

    def dataset_info(self):

        df = self.load_metadata()

        return {

            "Dataset": "ESC50",

            "Samples": len(df),

            "Classes": df["category"].nunique()
        }