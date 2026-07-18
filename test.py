import pandas as pd
from database.dataset_manager import DatasetManager

from loaders.esc50_loader import ESC50Loader
from loaders.urbansound8k_loader import UrbanSound8KLoader
from loaders.fsd50k_loader import FSD50KLoader
from loaders.emergency_loader import EmergencyLoader

manager = DatasetManager()

manager.add_dataset(ESC50Loader("datasets/ESC50").load())
manager.add_dataset(UrbanSound8KLoader("datasets/UrbanSound8K").load())
manager.add_dataset(FSD50KLoader("datasets/FSD50K").load())
manager.add_dataset(EmergencyLoader("datasets/Emergency").load())

df = manager.build()

labels = set()

for value in df["original_label"]:
    if isinstance(value, list):
        labels.update([str(x).lower() for x in value])
    else:
        labels.add(str(value).lower())

print("\n".join(sorted(labels)))