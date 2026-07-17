"""
Test Metadata Builder
"""

from managers.dataset_manager import DatasetManager
from managers.metadata_builder import MetadataBuilder


def main():

    print("=" * 60)
    print("BUILDING RAW DATASET")
    print("=" * 60)

    manager = DatasetManager()

    raw_dataframe = manager.build()

    print()

    print("=" * 60)
    print("BUILDING FINAL METADATA")
    print("=" * 60)

    builder = MetadataBuilder()

    metadata = builder.build(raw_dataframe)

    print()

    print(metadata.head())

    print()

    print("=" * 60)

    print(metadata["unified_label"].value_counts())

    print("=" * 60)

    builder.save(metadata)


if __name__ == "__main__":

    main()