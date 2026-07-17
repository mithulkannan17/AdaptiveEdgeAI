import pandas as pd

from pathlib import Path

from .base_loader import BaseDatasetLoader


class FSD50KLoader(BaseDatasetLoader):

    def load_metadata(self):

        metadata = self.dataset_path / "meta" / "fsd50k.csv"

        return pd.read_csv(metadata)

    def dataset_info(self):

        df = self.load_metadata()

        return {

            "Dataset": "FSD50K",

            "Samples": len(df),

            "Classes": df["category"].nunique()
        }