"""
Production Dataset for Environmental Sound Classification
"""

from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset

from training.label_encoder import LabelEncoder


class EnvironmentalDataset(Dataset):

    def __init__(
        self,
        dataframe: pd.DataFrame,
        transform=None,
        training=False,
    ):

        self.dataframe = dataframe.reset_index(drop=True)

        self.transform = transform

        self.training = training

        self.encoder = LabelEncoder()

    def __len__(self):

        return len(self.dataframe)

    def __getitem__(self, index):

        row = self.dataframe.iloc[index]

        spectrogram = np.load(row["spectrogram_path"])

        spectrogram = torch.from_numpy(
            spectrogram
        ).float()

        spectrogram = spectrogram.unsqueeze(0)

        if self.transform is not None:

            spectrogram = self.transform(
                spectrogram
            )

        label = torch.tensor(

            self.encoder.encode(
                row["unified_label"]
            ),

            dtype=torch.long

        )

        sample = {

            "spectrogram": spectrogram,

            "label": label,

            "sample_id": row["sample_id"],

            "filepath": row["filepath"]

        }

        return sample