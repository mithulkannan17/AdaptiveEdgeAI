from pathlib import Path

# Root Directory
ROOT_DIR = Path(__file__).resolve().parent.parent

# Dataset Paths
DATASETS = {
    "esc50": ROOT_DIR / "datasets" / "esc50",
    "fsd50k": ROOT_DIR / "datasets" / "fsd50k",
    "urbansound8k": ROOT_DIR / "datasets" / "urbansound8k",
    "emergency": ROOT_DIR / "datasets" / "emergency"
}

# Output Directory
OUTPUT_DIR = ROOT_DIR / "outputs"