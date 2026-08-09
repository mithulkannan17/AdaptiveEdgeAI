from training.datamodule import EnvironmentalDataModule


def main():

    datamodule = EnvironmentalDataModule(
        batch_size=16
    )

    datamodule.setup()

    print("=" * 60)

    print("Train Samples :", len(datamodule.train_dataset))

    print("Validation Samples :", len(datamodule.validation_dataset))

    print("Test Samples :", len(datamodule.test_dataset))

    print("=" * 60)

    loader = datamodule.train_dataloader()

    batch = next(iter(loader))

    print("Batch Keys")

    print(batch.keys())

    print()

    print("Spectrogram Shape")

    print(batch["spectrogram"].shape)

    print()

    print("Labels")

    print(batch["label"][:10])


if __name__ == "__main__":
    main()