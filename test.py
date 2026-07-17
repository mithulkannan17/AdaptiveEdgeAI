import pandas as pd
from collections import Counter

df = pd.read_csv("datasets/FSD50K/Metadata/dev.csv")   # adjust path if needed

counter = Counter()

for labels in df["labels"]:
    for label in str(labels).split(","):
        counter[label.strip()] += 1

print("Total unique labels:", len(counter))
print()

for label, count in counter.most_common(100):
    print(f"{label:45} {count}")