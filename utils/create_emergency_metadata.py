from pathlib import Path
import pandas as pd

ROOT = Path("datasets/emergency")

metadata_dir = ROOT / "Metadata"
audio_root = ROOT / "Extracted"

rows = []

# Ambulance
for audio in (audio_root / "Emergency Vehicle Sirens").glob("*.wav"):

    rows.append({
        "filename": audio.name,
        "label": "Ambulance",
        "audio_folder": "Emergency Vehicle Sirens"
    })


# Road
for audio in (audio_root / "Road Noises").glob("*.wav"):

    rows.append({
        "filename": audio.name,
        "label": "Road",
        "audio_folder": "Road Noises"
    })


df = pd.DataFrame(rows)

output = metadata_dir / "emergency_metadata.csv"

df.to_csv(output, index=False)

print(df.head())

print()

print(f"Saved {len(df)} samples")

print(output)