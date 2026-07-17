"""
metadata_builder.py

Builds unified metadata from all datasets.
Supports:
- Single-label datasets (ESC-50, UrbanSound8K)
- Multi-label datasets (FSD50K)
"""

from pathlib import Path
import ast

import pandas as pd

from utils.label_mapper import LabelMapper
from utils.sample_id_generator import SampleIDGenerator


class MetadataBuilder:

    def __init__(self):

        self.mapper = LabelMapper()
        self.id_generator = SampleIDGenerator()

    def _extract_labels(self, original_label):
        """
        Convert any label format into a list of clean labels.

        Supported formats:
        ------------------
        speech

        "speech"

        ['Thunder', 'Rain']

        "['Thunder', 'Rain']"

        "Thunder,Rain"

        ["Thunder","Rain"]
        """

        if original_label is None:
            return []

        # Already a Python list
        if isinstance(original_label, list):
            return [str(x).strip() for x in original_label]

        # Everything else becomes string
        text = str(original_label).strip()

        if not text:
            return []

        # String representation of a Python list
        if text.startswith("[") and text.endswith("]"):

            try:

                parsed = ast.literal_eval(text)

                if isinstance(parsed, list):
                    return [str(x).strip() for x in parsed]

            except Exception:
                pass

        # Comma separated labels
        if "," in text:

            return [
                x.strip().strip("'").strip('"')
                for x in text.split(",")
            ]

        return [text]

    def build(self, dataframe: pd.DataFrame) -> pd.DataFrame:

        rows = []

        total = len(dataframe)

        mapped = 0

        unmapped = 0

        for _, row in dataframe.iterrows():

            labels = self._extract_labels(row["original_label"])

            unified_label = "UNMAPPED"

            for label in labels:

                mapped_label = self.mapper.map_label(label)

                if mapped_label != "UNMAPPED":

                    unified_label = mapped_label
                    break

            if unified_label == "UNMAPPED":

                unmapped += 1
                continue

            mapped += 1

            rows.append({

                "sample_id":
                    self.id_generator.generate(row["dataset"]),

                "dataset":
                    row["dataset"],

                "filepath":
                    row["filepath"],

                "filename":
                    row["filename"],

                "original_label":
                    row["original_label"],

                "unified_label":
                    unified_label,

                "split":
                    row.get("split", ""),

                "fold":
                    row.get("fold", "")

            })

        print("\n" + "=" * 60)
        print("Metadata Builder Summary")
        print("=" * 60)
        print(f"Total Samples : {total}")
        print(f"Mapped        : {mapped}")
        print(f"Unmapped      : {unmapped}")
        print("=" * 60)

        return pd.DataFrame(rows)

    def save(

        self,

        dataframe: pd.DataFrame,

        output_file="database/metadata.csv"

    ):

        output_file = Path(output_file)

        output_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        dataframe.to_csv(
            output_file,
            index=False
        )

        print(f"\nMetadata saved to: {output_file}")