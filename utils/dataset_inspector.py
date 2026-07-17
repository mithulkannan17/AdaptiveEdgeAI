"""
dataset_inspector.py

Inspects audio files and extracts metadata.
"""

from pathlib import Path
from typing import List, Dict
import soundfile as sf
import pandas as pd
from tqdm import tqdm
import logging


class DatasetInspector:

    def __init__(self):

        self.logger = logging.getLogger(self.__class__.__name__)

    def get_duration_category(self, duration: float) -> str:
        """
        Categorize audio clips based on duration.
        """
        if duration < 2.0:
            return "Very Short"
        elif duration > 2.0 and duration < 5.0:
            return "Short"
        elif duration == 5.0:
            return "Normal"
        elif duration > 5.0 and duration < 15.0:
            return "Long"
        else:
            return "Very Long"

    def inspect(self, audio_files: List[Path], dataset_name: str):

        records = []

        self.logger.info(
            f"Inspecting {len(audio_files)} files..."
        )

        for file in tqdm(audio_files):

            try:

                info = sf.info(file)

                records.append({

                    "dataset": dataset_name,

                    "filename": file.name,

                    "filepath": str(file),

                    "extension": file.suffix,

                    "duration": round(info.duration, 3),

                    "duration_category": self.get_duration_category(round(info.duration, 3)),

                    "samplerate": info.samplerate,

                    "channels": info.channels,

                    "format": info.format,

                    "subtype": info.subtype,

                    "filesize_mb": round(file.stat().st_size / 1024 / 1024, 3),

                    "corrupted": False

                })

            except Exception:

                records.append({

                    "dataset": dataset_name,

                    "filename": file.name,

                    "filepath": str(file),

                    "extension": file.suffix,

                    "duration": None,

                    "samplerate": None,

                    "channels": None,

                    "format": None,

                    "subtype": None,

                    "filesize_mb": None,

                    "corrupted": None

                })

        return pd.DataFrame(records)
    
    