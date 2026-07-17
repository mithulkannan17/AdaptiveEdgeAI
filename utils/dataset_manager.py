from pathlib import Path
from config.settings import DATASETS
from utils.dataset_inspector import DatasetInspector

class DatasetManager:

    def __init__(self):
        self.datasets = DATASETS

    def show_available_datasets(self):

        print("=" * 50)
        print("AVAILABLE DATASETS")
        print("=" * 50)

        for name, path in self.datasets.items():

            exists = "✓" if Path(path).exists() else "✗"

            print(f"{exists} {name} -> {path}")

    def inspect_all_datasets(self):

        print()

        print("=" * 50)
        print("DATASET INSPECTION")
        print("=" * 50)

        for _, path in self.datasets.items():

            DatasetInspector.folder_statistics(path)

            print("-" * 50)