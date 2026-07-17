import numpy as np

from feature_extraction.batch_feature_extractor import BatchFeatureExtractor
from feature_extraction.visualization import show_spectrogram


def main():

    extractor = BatchFeatureExtractor()

    extractor.process_dataset()

    sample = np.load(

        "processed/spectrograms/ESC50_000001.npy"

    )

    print(sample.shape)

    show_spectrogram(sample)


if __name__ == "__main__":

    main()