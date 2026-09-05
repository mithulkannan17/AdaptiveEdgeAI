from loaders.esc50_loader import ESC50Loader

loader = ESC50Loader("datasets/ESC50")

df = loader.load()

print(df.head())

print()

print(df.columns.tolist())

print()

print(df["original_label"].value_counts().head())