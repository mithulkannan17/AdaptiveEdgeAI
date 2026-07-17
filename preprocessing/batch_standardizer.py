"""
Batch Audio Standardizer

Processes the entire dataset into a standardized format.
Unreadable/corrupted audio files are skipped and logged.
"""

from pathlib import Path

import pandas as pd
from tqdm import tqdm

from preprocessing.audio_standardizer import AudioStandardizer


class BatchStandardizer:

    def __init__(self):

        self.standardizer = AudioStandardizer()

    def process_dataset(
        self,
        metadata_csv="database/metadata.csv",
        output_folder="processed/audio",
        output_metadata="database/processed_metadata.csv",
        failed_metadata="database/failed_audio.csv"
    ):

        metadata = pd.read_csv(metadata_csv)

        processed_rows = []
        failed_rows = []

        output_folder = Path(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)

        for _, row in tqdm(
            metadata.iterrows(),
            total=len(metadata),
            desc="Standardizing Audio"
        ):

            input_audio = Path(row["filepath"])

            output_audio = (
                output_folder /
                row["sample_id"]
            ).with_suffix(".wav")

            try:

                info = self.standardizer.process(
                    input_audio,
                    output_audio
                )

                new_row = row.copy()

                new_row["processed_path"] = str(output_audio)
                new_row["sample_rate"] = info["sample_rate"]
                new_row["duration"] = info["duration"]
                new_row["channels"] = info["channels"]

                processed_rows.append(new_row)

            except Exception as e:

                failed_rows.append({
                    "sample_id": row["sample_id"],
                    "dataset": row["dataset"],
                    "filepath": str(input_audio),
                    "error": str(e)
                })

                continue

        processed = pd.DataFrame(processed_rows)

        processed.to_csv(
            output_metadata,
            index=False
        )

        if failed_rows:

            failed = pd.DataFrame(failed_rows)

            failed.to_csv(
                failed_metadata,
                index=False
            )

        print()

        print("=" * 60)
        print("Audio Standardization Completed")
        print("=" * 60)

        print(f"Total Samples      : {len(metadata)}")
        print(f"Successfully Done  : {len(processed_rows)}")
        print(f"Failed             : {len(failed_rows)}")

        print()

        print(f"Processed Metadata : {output_metadata}")

        if failed_rows:
            print(f"Failed Log         : {failed_metadata}")

        print("=" * 60)