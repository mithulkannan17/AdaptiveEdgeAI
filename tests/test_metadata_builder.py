from collections import Counter

from managers.dataset_manager import DatasetManager
from managers.metadata_builder import MetadataBuilder


manager = DatasetManager()
raw = manager.build()

print("=" * 70)
print("RAW DATASET DISTRIBUTION")
print("=" * 70)
print(raw["dataset"].value_counts())

builder = MetadataBuilder()

counter = Counter()

for _, row in raw.iterrows():

    labels = builder._extract_labels(row["original_label"])

    mapped = False

    for label in labels:

        unified = builder.mapper.map_label(label)

        if unified != "UNMAPPED":

            counter[unified] += 1
            mapped = True
            break

    if not mapped:
        counter["UNMAPPED"] += 1

print()
print("=" * 70)
print("MAPPING RESULT")
print("=" * 70)

for k, v in counter.items():
    print(f"{k:20} {v}")