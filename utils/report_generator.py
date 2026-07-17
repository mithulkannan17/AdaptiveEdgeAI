"""
Generates summary statistics for datasets.
"""

import pandas as pd


class ReportGenerator:

    @staticmethod
    def summarize(df: pd.DataFrame):

        print("\n========== DATASET REPORT ==========")

        print(f"Total Files      : {len(df)}")

        print(f"Corrupted Files  : {df['corrupted'].sum()}")

        print(f"Datasets         : {df['dataset'].nunique()}")

        print("\nFiles Per Dataset")

        print(df.groupby("dataset").size())

        print("\nSample Rates")

        print(df["samplerate"].value_counts())

        print("\nChannels")

        print(df["channels"].value_counts())

        print("\nAverage Duration")

        print(df["duration"].mean())

        print("\nDuration Categories")
        
        print(df["duration_category"].value_counts())