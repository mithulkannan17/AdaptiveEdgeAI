"""
Create stratified train/validation/test splits.
"""

from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split


class DatasetSplitter:

    def __init__(
        self,
        train_ratio=0.70,
        val_ratio=0.15,
        test_ratio=0.15,
        random_state=42
    ):
        if abs(train_ratio + val_ratio + test_ratio - 1.0) > 1e-6:
            raise ValueError("Split ratios must sum to 1.")

        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio
        self.random_state = random_state

    def split(self, metadata_csv):

        df = pd.read_csv(metadata_csv)

        train_df, temp_df = train_test_split(
            df,
            test_size=(1 - self.train_ratio),
            stratify=df["unified_label"],
            random_state=self.random_state,
        )

        val_ratio_adjusted = self.val_ratio / (self.val_ratio + self.test_ratio)

        val_df, test_df = train_test_split(
            temp_df,
            test_size=(1 - val_ratio_adjusted),
            stratify=temp_df["unified_label"],
            random_state=self.random_state,
        )

        train_df = train_df.copy()
        val_df = val_df.copy()
        test_df = test_df.copy()

        train_df["split"] = "train"
        val_df["split"] = "validation"
        test_df["split"] = "test"

        final_df = pd.concat(
            [train_df, val_df, test_df],
            ignore_index=True
        )

        final_df = final_df.sort_values("sample_id")

        return final_df

    def save(
        self,
        dataframe,
        output_file="database/spectrogram_metadata.csv"
    ):
        output_file = Path(output_file)

        dataframe.to_csv(output_file, index=False)

        print(f"\nSaved split metadata to {output_file}")