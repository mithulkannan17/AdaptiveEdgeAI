"""
Dynamic Label Encoder

Builds label mappings directly from the metadata.

The encoder intentionally uses Python's built-in CSV reader
instead of pandas so that inference does not depend on the
pandas / PyArrow native stack.
"""

from __future__ import annotations

import csv
from pathlib import Path


class LabelEncoder:
    """
    Build a deterministic label-to-index mapping from the
    spectrogram metadata CSV.
    """

    def __init__(
        self,
        metadata_csv: str | Path = (
            "database/spectrogram_metadata.csv"
        ),
    ) -> None:

        metadata_csv = Path(
            metadata_csv
        )

        if not metadata_csv.exists():

            raise FileNotFoundError(
                metadata_csv
            )

        # --------------------------------------------------
        # Read metadata
        # --------------------------------------------------

        labels: set[str] = set()

        with metadata_csv.open(
            mode="r",
            encoding="utf-8-sig",
            newline="",
        ) as file:

            reader = csv.DictReader(
                file
            )

            if reader.fieldnames is None:

                raise ValueError(
                    "Metadata CSV does not contain a header."
                )

            if "unified_label" not in reader.fieldnames:

                raise KeyError(
                    "Metadata CSV must contain "
                    "'unified_label' column."
                )

            for row in reader:

                label = row.get(
                    "unified_label"
                )

                if label is None:

                    continue

                label = label.strip()

                if not label:

                    continue

                labels.add(
                    label
                )

        # --------------------------------------------------
        # Deterministic class ordering
        # --------------------------------------------------

        classes = sorted(
            labels
        )

        self.classes = classes

        # --------------------------------------------------
        # Label → Index
        # --------------------------------------------------

        self.label_to_index = {

            label: index

            for index, label
            in enumerate(
                classes
            )

        }

        # --------------------------------------------------
        # Index → Label
        # --------------------------------------------------

        self.index_to_label = {

            index: label

            for label, index
            in self.label_to_index.items()

        }

    # ======================================================
    # Encoding
    # ======================================================

    def encode(
        self,
        label: str,
    ) -> int:
        """
        Convert a class label into its integer index.
        """

        return self.label_to_index[
            label
        ]

    # ======================================================
    # Decoding
    # ======================================================

    def decode(
        self,
        index: int,
    ) -> str:
        """
        Convert an integer class index into its label.
        """

        return self.index_to_label[
            index
        ]

    # ======================================================
    # Number of Classes
    # ======================================================

    def num_classes(
        self,
    ) -> int:
        """
        Return the number of discovered classes.
        """

        return len(
            self.classes
        )

    # ======================================================
    # Summary
    # ======================================================

    def print_summary(
        self,
    ) -> None:
        """
        Print the complete label mapping.
        """

        print()

        print(
            "=" * 60
        )

        print(
            "Label Encoder"
        )

        print(
            "=" * 60
        )

        print(
            f"Number of Classes : "
            f"{self.num_classes()}"
        )

        print()

        for index, label in enumerate(
            self.classes
        ):

            print(
                f"{index:2d} -> {label}"
            )

        print(
            "=" * 60
        )