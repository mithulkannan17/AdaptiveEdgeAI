"""
dataset_manager.py

Combines all dataset loaders into a single DataFrame.
"""

import pandas as pd

from loaders.esc50_loader import ESC50Loader
from loaders.urbansound8k_loader import UrbanSound8KLoader
from loaders.fsd50k_loader import FSD50KLoader
from loaders.emergency_loader import EmergencyLoader
from loaders.birdclef_loader import BirdCLEFLoader
from loaders.animals_loader import AnimalsLoader


class DatasetManager:

    def __init__(self):

        self.loaders = [

            ESC50Loader("datasets/ESC50"),

            UrbanSound8KLoader("datasets/urbansound8k"),

            FSD50KLoader("datasets/FSD50K"),

            EmergencyLoader("datasets/emergency"),

            BirdCLEFLoader("datasets/BirdCLEF/birdclef-2026"),

            AnimalsLoader("datasets/Animals/Animal-SDataset")

        ]

    def build(self):

        frames = []

        for loader in self.loaders:

            print(f"Loading {loader.DATASET_NAME}")

            frames.append(loader.load())

        return pd.concat(

            frames,

            ignore_index=True

        )
    
if __name__ == "__main__":

    manager = DatasetManager()

    df = manager.build()

    print(df.head())

    print(f"\nTotal samples: {len(df)}")