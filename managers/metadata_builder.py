"""
metadata_builder.py

Builds the final metadata.csv used by the entire project.
"""

from pathlib import Path

import pandas as pd

from utils.label_mapper import LabelMapper
from utils.sample_id_generator import SampleIDGenerator


class MetadataBuilder:

    def __init__(self):

        self.mapper = LabelMapper()

        self.id_generator = SampleIDGenerator()

    def build(self, dataframe: pd.DataFrame) -> pd.DataFrame:

        rows = []

        for _, row in dataframe.iterrows():

            original = row["original_label"]

            # Handle multi-label datasets (FSD50K)
            if isinstance(original, list):

                mapped = None

                for label in original:

                    unified = self.mapper.map_label(label)

                    if unified != "UNMAPPED":

                        mapped = unified

                        break

            else:

                mapped = self.mapper.map_label(original)

            if mapped == "UNMAPPED":
                continue

            rows.append({

                "sample_id":
                    self.id_generator.generate(
                        row["dataset"]
                    ),

                "dataset":
                    row["dataset"],

                "filepath":
                    row["filepath"],

                "filename":
                    row["filename"],

                "original_label":
                    original,

                "unified_label":
                    mapped,

                "split":
                    row["split"],

                "fold":
                    row["fold"]

            })

        return pd.DataFrame(rows)

    def save(
        self,
        dataframe: pd.DataFrame,
        output_file="database/metadata.csv"
    ):

        output = Path(output_file)

        output.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        dataframe.to_csv(
            output,
            index=False
        )

        print(f"\nSaved {output}")