"""
Configuration Manager
"""

from pathlib import Path
import yaml


class ConfigManager:

    def __init__(self, config_directory="config"):

        self.config_directory = Path(config_directory)

        self._cache = {}

    def load(self, filename):

        path = self.config_directory / filename

        if filename in self._cache:
            return self._cache[filename]

        if not path.exists():
            raise FileNotFoundError(path)

        with open(path, "r", encoding="utf-8") as file:

            config = yaml.safe_load(file)

        self._cache[filename] = config

        return config

    def training(self):

        return self.load("training_config.yaml")

    def model(self):

        return self.load("model_config.yaml")

    def dataset(self):

        return self.load("dataset_config.yaml")

    def inference(self):

        return self.load("inference_config.yaml")

    def hardware(self):

        return self.load("hardware_config.yaml")