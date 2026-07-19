"""
Metadata Builder

Combines all dataset loaders into a unified metadata.csv
"""

import ast
from pathlib import Path

import pandas as pd

from database.dataset_manager import DatasetManager

from loaders.esc50_loader import ESC50Loader
from loaders.urbansound8k_loader import UrbanSound8KLoader
from loaders.fsd50k_loader import FSD50KLoader
from loaders.emergency_loader import EmergencyLoader
from loaders.birdclef_loader import BirdCLEFLoader
from loaders.animals_loader import AnimalsLoader

from utils.label_mapper import LabelMapper


class MetadataBuilder:

    def __init__(self):

        self.manager = DatasetManager()

        self.mapper = LabelMapper()

    def load_datasets(self):

        print("Loading ESC50...")
        self.manager.add_dataset(
            ESC50Loader("datasets/ESC50").load()
        )

        print("Loading UrbanSound8K...")
        self.manager.add_dataset(
            UrbanSound8KLoader("datasets/urbansound8k").load()
        )

        print("Loading FSD50K...")
        self.manager.add_dataset(
            FSD50KLoader("datasets/FSD50K").load()
        )

        print("Loading Emergency...")
        self.manager.add_dataset(
            EmergencyLoader("datasets/emergency").load()
        )

        print("Loading BirdCLEF2026...")
        self.manager.add_dataset(
            BirdCLEFLoader("datasets/BirdCLEF/birdclef-2026").load()
        )

        print("Loading Animals...")
        self.manager.add_dataset(
            AnimalsLoader("datasets/Animals/Animal-SDataset").load()
        )

        return self.manager.build()

    def build(self):

        df = self.load_datasets()

        metadata = []

        mapped = 0

        unmapped = 0

        for idx, row in df.iterrows():

            labels = row["original_label"]

            if isinstance(labels, str):

                try:

                    labels = ast.literal_eval(labels)

                except Exception:

                    labels = [labels]

            if not isinstance(labels, list):

                labels = [labels]

            unified = None

            for label in labels:

                mapped_label = self.mapper.map_label(label)

                if mapped_label != "UNMAPPED":

                    unified = mapped_label

                    break

            if unified is None:

                unmapped += 1

                continue

            metadata.append({

                "sample_id": f"{row['dataset']}_{idx:06d}",

                "dataset": row["dataset"],

                "filepath": row["filepath"],

                "filename": row["filename"],

                "original_label": labels,

                "unified_label": unified,

                "split": row["split"],

                "fold": row["fold"]

            })

            mapped += 1

        metadata = pd.DataFrame(metadata)

        output = Path("database/metadata.csv")

        output.parent.mkdir(exist_ok=True)

        metadata.to_csv(output, index=False)

        print()

        print("=" * 60)
        print("Metadata Generation Complete")
        print("=" * 60)

        print(f"Total Samples    : {len(df)}")
        print(f"Mapped Samples   : {mapped}")
        print(f"Unmapped Samples : {unmapped}")

        print("\nDataset Distribution")
        print(metadata["dataset"].value_counts())

        print("\nUnified Label Distribution")
        print(metadata["unified_label"].value_counts())

        print(f"\nSaved : {output}")

        return metadata


if __name__ == "__main__":

    MetadataBuilder().build()