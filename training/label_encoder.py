"""
Dynamic Label Encoder

Builds label mappings directly from the metadata.
"""

from pathlib import Path

import pandas as pd


class LabelEncoder:

    def __init__(

        self,

        metadata_csv="database/spectrogram_metadata.csv"

    ):

        metadata_csv = Path(metadata_csv)

        if not metadata_csv.exists():

            raise FileNotFoundError(metadata_csv)

        df = pd.read_csv(metadata_csv)

        classes = sorted(

            df["unified_label"]

            .dropna()

            .unique()

            .tolist()

        )

        self.classes = classes

        self.label_to_index = {

            label: index

            for index, label in enumerate(classes)

        }

        self.index_to_label = {

            index: label

            for label, index

            in self.label_to_index.items()

        }

    def encode(self, label):

        return self.label_to_index[label]

    def decode(self, index):

        return self.index_to_label[index]

    def num_classes(self):

        return len(self.classes)

    def print_summary(self):

        print()

        print("=" * 60)

        print("Label Encoder")

        print("=" * 60)

        print(f"Number of Classes : {self.num_classes()}")

        print()

        for index, label in enumerate(self.classes):

            print(f"{index:2d} -> {label}")

        print("=" * 60)