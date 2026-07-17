"""
dataset_scanner.py

Scans dataset folders and returns all supported audio files.
"""

from pathlib import Path
from typing import List
import logging


class DatasetScanner:
    """
    Scans a dataset directory recursively for audio files.
    """

    SUPPORTED_EXTENSIONS = {
        ".wav",
        ".mp3",
        ".flac",
        ".ogg"
    }

    def __init__(self):

        self.logger = logging.getLogger(self.__class__.__name__)

    def scan(self, dataset_path: Path) -> List[Path]:

        dataset_path = Path(dataset_path)

        if not dataset_path.exists():
            raise FileNotFoundError(
                f"Dataset not found: {dataset_path}"
            )

        audio_files = []

        for file in dataset_path.rglob("*"):

            if file.suffix.lower() in self.SUPPORTED_EXTENSIONS:

                audio_files.append(file)

        self.logger.info(
            f"{dataset_path.name}: {len(audio_files)} audio files found."
        )

        return sorted(audio_files)

    def count(self, dataset_path: Path) -> int:

        return len(self.scan(dataset_path))