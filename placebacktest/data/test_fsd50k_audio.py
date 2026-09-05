from pathlib import Path
import librosa
import soundfile as sf

files = [
    "datasets/FSD50K/Extracted/FSD50K.dev_audio/64760.wav",
    "datasets/FSD50K/Extracted/FSD50K.dev_audio/64761.wav",
    "datasets/FSD50K/Extracted/FSD50K.dev_audio/40515.wav",
]

for file in files:

    print("=" * 60)
    print(file)

    path = Path(file)

    print("Exists:", path.exists())
    print("Size:", path.stat().st_size)

    try:
        info = sf.info(path)
        print("SoundFile: OK")
        print(info)
    except Exception as e:
        print("SoundFile ERROR:", e)

    try:
        audio, sr = librosa.load(path, sr=None)
        print("Librosa: OK")
        print("Samples:", len(audio))
        print("Sample Rate:", sr)
    except Exception as e:
        print("Librosa ERROR:", e)