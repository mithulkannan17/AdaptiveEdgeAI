from pathlib import Path
import numpy as np
import torch
from torch.utils.data import Dataset


class EnvironmentalSoundDataset(Dataset):

    def __init__(self, feature_paths, labels):

        self.feature_paths = feature_paths
        self.labels = labels

    def __len__(self):

        return len(self.feature_paths)

    def __getitem__(self, index):

        feature = np.load(self.feature_paths[index])

        feature = torch.tensor(
            feature,
            dtype=torch.float32
        )

        label = torch.tensor(
            self.labels[index],
            dtype=torch.long
        )

        return feature, label