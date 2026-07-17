import torch

from training.datamodule import create_dataloader


def main():

    loader = create_dataloader(

        "database/spectrogram_metadata.csv",

        batch_size=16

    )

    images, labels = next(iter(loader))

    print()

    print(images.shape)

    print(labels.shape)

    print(labels)

    print()

    print(images.dtype)

    print(labels.dtype)


if __name__ == "__main__":

    main()