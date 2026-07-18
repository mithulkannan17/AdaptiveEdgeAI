"""
Batch Log-Mel Feature Extractor
"""

from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

from feature_extraction.log_mel_extractor import LogMelExtractor


class BatchFeatureExtractor:

    def __init__(self):

        self.extractor = LogMelExtractor()

    def process_dataset(

        self,

        metadata_csv="database/processed_metadata.csv",

        output_folder="processed/spectrograms",

        output_metadata="database/spectrogram_metadata.csv"

    ):

        metadata = pd.read_csv(metadata_csv)

        output_folder = Path(output_folder)

        output_folder.mkdir(
            parents=True,
            exist_ok=True
        )

        processed_rows = []

        for _, row in tqdm(

            metadata.iterrows(),

            total=len(metadata),

            desc="Extracting Spectrograms"

        ):

            spec = self.extractor.extract(

                row["processed_path"]

            )

            output_file = (

                output_folder /

                row["sample_id"]

            ).with_suffix(".npy")

            np.save(

                output_file,

                spec

            )

            row = row.copy()

            row["spectrogram_path"] = str(output_file)

            row["height"] = spec.shape[0]

            row["width"] = spec.shape[1]

            processed_rows.append(row)

        processed = pd.DataFrame(processed_rows)

        processed.to_csv(

            output_metadata,

            index=False

        )

        print()

        print("=" * 60)

        print("Feature Extraction Completed")

        print("=" * 60)

        print(f"Processed : {len(processed)}")

        print(f"Saved : {output_metadata}")

        print("=" * 60)

if __name__ == "__main__":

    BatchFeatureExtractor().process_dataset()