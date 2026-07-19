"""
Metadata Balancer

Balances metadata by downsampling majority classes.
"""

from pathlib import Path

import pandas as pd


class MetadataBalancer:

    def __init__(

        self,

        input_csv="database/metadata.csv",

        output_csv="database/balanced_metadata.csv",

        max_samples_per_class=6000,

        random_seed=42

    ):

        self.input_csv = Path(input_csv)

        self.output_csv = Path(output_csv)

        self.max_samples = max_samples_per_class

        self.random_seed = random_seed

    def balance(self):

        df = pd.read_csv(self.input_csv)

        balanced = []

        print("=" * 60)
        print("Balancing Dataset")
        print("=" * 60)

        for label, group in df.groupby("unified_label"):

            original = len(group)

            if original > self.max_samples:

                group = group.sample(

                    n=self.max_samples,

                    random_state=self.random_seed

                )

            balanced.append(group)

            print(

                f"{label:<20}"

                f"{original:>8} -> {len(group):>6}"

            )

        balanced_df = (

            pd.concat(

                balanced,

                ignore_index=True

            )

            .sample(

                frac=1,

                random_state=self.random_seed

            )

            .reset_index(drop=True)

        )

        self.output_csv.parent.mkdir(

            exist_ok=True

        )

        balanced_df.to_csv(

            self.output_csv,

            index=False

        )

        print()

        print("=" * 60)
        print("Balancing Complete")
        print("=" * 60)

        print(f"Original Samples : {len(df)}")
        print(f"Balanced Samples : {len(balanced_df)}")

        print()

        print("Final Distribution")

        print(

            balanced_df["unified_label"]

            .value_counts()

        )

        print()

        print(

            f"Saved : {self.output_csv}"

        )

        return balanced_df


if __name__ == "__main__":

    MetadataBalancer().balance()