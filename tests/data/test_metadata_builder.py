import pandas as pd

from managers.metadata_builder import MetadataBuilder


def main():

    builder = MetadataBuilder()

    df = builder.build()

    print()

    print(df.head())

    print()

    print("=" * 60)

    print("Class Distribution")

    print("=" * 60)

    print(df["unified_label"].value_counts())

    print()

    print("=" * 60)

    print("Dataset Distribution")

    print("=" * 60)

    print(df["dataset"].value_counts())


if __name__ == "__main__":

    main()