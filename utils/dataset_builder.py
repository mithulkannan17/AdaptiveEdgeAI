from pathlib import Path


class DatasetBuilder:

    def __init__(self):

        self.output = Path("data/raw")

    def build(self):

        print()

        print("=" * 50)

        print("BUILDING UNIFIED DATASET")

        print("=" * 50)