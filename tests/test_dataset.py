import pandas as pd

from training.dataset import EnvironmentalDataset


def main():

    df = pd.read_csv(
        "database/spectrogram_metadata.csv"
    )

    dataset = EnvironmentalDataset(df)

    sample = dataset[0]

    print()

    print(sample.keys())

    print(sample["spectrogram"].shape)

    print(sample["label"])

    print(sample["sample_id"])

    print(sample["filepath"])


if __name__ == "__main__":

    main()