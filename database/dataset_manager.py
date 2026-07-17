"""
dataset_manager.py

Combines multiple dataset loaders into one unified metadata table.
"""

from pathlib import Path

import pandas as pd


class DatasetManager:

    def __init__(self):

        self.datasets = []

    def add_dataset(self, dataframe):

        self.datasets.append(dataframe)

    def build(self):

        if not self.datasets:
            raise ValueError("No datasets loaded.")

        df = pd.concat(

            self.datasets,

            ignore_index=True

        )

        return df

    def save(self, dataframe, output_path):

        output_path = Path(output_path)

        output_path.parent.mkdir(

            parents=True,

            exist_ok=True

        )

        dataframe.to_csv(

            output_path,

            index=False

        )

        print(f"Saved {len(dataframe)} samples.")
