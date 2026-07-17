"""
base_loader.py

Abstract base class for all dataset loaders.
"""

from abc import ABC, abstractmethod


class BaseDatasetLoader(ABC):

    @abstractmethod
    def load(self):
        """
        Return dataset records.
        """
        pass