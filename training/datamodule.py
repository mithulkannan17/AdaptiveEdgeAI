"""
PyTorch DataLoader
"""

from torch.utils.data import DataLoader

from training.dataset import EnvironmentalSoundDataset


def create_dataloader(

    metadata_csv,

    batch_size=32,

    shuffle=True,

    workers=4

):

    dataset = EnvironmentalSoundDataset(

        metadata_csv

    )

    loader = DataLoader(

        dataset,

        batch_size=batch_size,

        shuffle=shuffle,

        num_workers=workers,

        pin_memory=True

    )

    return loader