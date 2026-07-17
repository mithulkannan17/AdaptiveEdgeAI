from pathlib import Path

print(len(list(Path("datasets/emergency/Extracted/Emergency Vehicle Sirens").iterdir())))
print(len(list(Path("datasets/emergency/Extracted/Road Noises").iterdir())))