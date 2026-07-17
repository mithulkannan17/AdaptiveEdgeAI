"""
dataset_validator.py
"""

from pathlib import Path


class DatasetValidator:

    @staticmethod
    def validate(df):

        print("\n========== DATASET VALIDATION ==========\n")

        total_samples = len(df)

        missing_files = (

            ~df["filepath"].apply(

                lambda path: Path(path).exists()

            )

        ).sum()

        duplicate_files = (

            df["filepath"]

            .duplicated()

            .sum()

        )

        missing_labels = (

            df["original_label"]

            .isna()

            .sum()

        )

        print(f"Total Samples      : {total_samples}")

        print(f"Missing Audio      : {missing_files}")

        print(f"Duplicate Files    : {duplicate_files}")

        print(f"Missing Labels     : {missing_labels}")

        print("\nValidation Finished.\n")