"""
PyTorch Dataset
"""

from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset

from training.label_encoder import LabelEncoder


class EnvironmentalSoundDataset(Dataset):

    def __init__(self, metadata_csv):

        self.metadata = pd.read_csv(metadata_csv)

        self.encoder = LabelEncoder()

    def __len__(self):

        return len(self.metadata)

    def __getitem__(self, index):

        row = self.metadata.iloc[index]

        spec = np.load(row["spectrogram_path"])

        spec = torch.tensor(
            spec,
            dtype=torch.float32
        )

        spec = spec.unsqueeze(0)

        label = torch.tensor(

            self.encoder.encode(
                row["unified_label"]
            ),

            dtype=torch.long

        )

        return spec, label