"""
DataModule

Creates train/validation/test datasets and dataloaders.
"""

from pathlib import Path

import pandas as pd

from sklearn.model_selection import train_test_split

from torch.utils.data import DataLoader

from torch.utils.data import (
    DataLoader,
    WeightedRandomSampler
)

from training.augmentations import (
    training_augmentation,
    validation_augmentation
)

from collections import Counter
import torch

from training.dataset import EnvironmentalDataset

class EnvironmentalDataModule:

    def __init__(
        self,
        metadata_csv="database/spectrogram_metadata.csv",
        batch_size=32,
        num_workers=4,
        test_size=0.15,
        validation_size=0.15,
        random_state=42,
        train_transform=None,
        validation_transform=None,
        test_transform=None
    ):

        self.metadata_csv = Path(metadata_csv)

        self.batch_size = batch_size

        self.num_workers = num_workers

        self.test_size = test_size

        self.validation_size = validation_size

        self.random_state = random_state

        self.train_transform = (
            
            train_transform
            
            if train_transform is not None
            
            else training_augmentation()
            
            )

        self.validation_transform = (
            
            validation_transform
            
            if validation_transform is not None
            
            else validation_augmentation()
            
            )

        self.test_transform = (
            
            test_transform
            
            if test_transform is not None
            
            else validation_augmentation()
            
            )

        self.train_dataset = None
        self.validation_dataset = None
        self.test_dataset = None

    def setup(self):

        df = pd.read_csv(self.metadata_csv)

        train_df, test_df = train_test_split(
            df,
            test_size=self.test_size,
            random_state=self.random_state,
            stratify=df["unified_label"]
        )

        validation_ratio = self.validation_size / (1 - self.test_size)

        train_df, validation_df = train_test_split(
            train_df,
            test_size=validation_ratio,
            random_state=self.random_state,
            stratify=train_df["unified_label"]
        )

        self.train_dataset = EnvironmentalDataset(
            train_df,
            transform=self.train_transform,
            training=True
        )

        self.validation_dataset = EnvironmentalDataset(
            validation_df,
            transform=self.validation_transform,
            training=False
        )

        self.test_dataset = EnvironmentalDataset(
            test_df,
            transform=self.test_transform,
            training=False
        )

    def train_dataloader(self):

        return DataLoader(
            
            self.train_dataset,
            
            batch_size=self.batch_size,
            
            sampler=self.build_sampler(),
            
            num_workers=self.num_workers,
            
            pin_memory=True
            
            )

    def validation_dataloader(self):

        return DataLoader(
            self.validation_dataset,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=self.num_workers,
            pin_memory=True
        )

    def test_dataloader(self):

        return DataLoader(
            self.test_dataset,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=self.num_workers,
            pin_memory=True
        )
    
    def build_sampler(self):
        
        labels = self.train_dataset.dataframe["unified_label"]
        
        counts = Counter(labels)
        
        weights = {
            
            label: 1.0 / count
            
            for label, count in counts.items()
            
            }
        
        sample_weights = [
            
            weights[label]
            
            for label in labels
            
            ]
        
        sampler = WeightedRandomSampler(
            
            weights=torch.DoubleTensor(sample_weights),
            
            num_samples=len(sample_weights),
            
            replacement=True
            
            )
        
        return sampler