import pandas as pd

df = pd.read_csv("database/spectrogram_metadata.csv")

print(df["unified_label"].value_counts())
print()
print(df["unified_label"].nunique())
print(sorted(df["unified_label"].unique()))