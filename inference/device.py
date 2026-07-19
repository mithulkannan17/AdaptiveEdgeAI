"""
Device Selection Utility

Handles device selection for inference.
"""

import torch


class DeviceManager:
    """
    Utility class for selecting the inference device.
    """

    @staticmethod
    def get_device() -> torch.device:
        """
        Returns the best available device.

        Priority
        --------
        CUDA -> CPU
        """

        if torch.cuda.is_available():

            return torch.device("cuda")

        return torch.device("cpu")