"""
dataset_manager.py

Combines all dataset loaders into a single DataFrame.
"""

import pandas as pd

from loaders.esc50_loader import ESC50Loader
from loaders.urbansound8k_loader import UrbanSound8KLoader
from loaders.fsd50k_loader import FSD50KLoader
from loaders.emergency_loader import EmergencyLoader


class DatasetManager:

    def __init__(self):

        self.loaders = [

            ESC50Loader("datasets/ESC50"),

            UrbanSound8KLoader("datasets/urbansound8k"),

            FSD50KLoader("datasets/FSD50K"),

            EmergencyLoader("datasets/emergency")

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