from training.split import DatasetSplitter


def main():

    splitter = DatasetSplitter()

    df = splitter.split(
        "database/spectrogram_metadata.csv"
    )

    splitter.save(df)

    print("\nSamples per split\n")

    print(df["split"].value_counts())

    print("\nClass distribution\n")

    print(
        df.groupby(
            ["split", "unified_label"]
        ).size()
    )


if __name__ == "__main__":
    main()