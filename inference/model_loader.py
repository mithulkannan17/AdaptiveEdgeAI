"""
Model Loader

Loads trained deep learning models for inference.
"""

from pathlib import Path

import torch

from models.aura_cnn import AuraCNN


class ModelLoader:
    """
    Loads trained models for inference.
    """

    def __init__(
        self,
        checkpoint_path: str | Path,
        device: torch.device,
    ):

        self.checkpoint_path = Path(checkpoint_path)

        self.device = device

    def load(self) -> torch.nn.Module:
        """
        Loads the trained model.

        Returns
        -------
        torch.nn.Module
            Model ready for inference.
        """

        if not self.checkpoint_path.exists():

            raise FileNotFoundError(

                f"Checkpoint not found: {self.checkpoint_path}"

            )

        model = AuraCNN()

        checkpoint = torch.load(

            self.checkpoint_path,

            map_location=self.device

        )

        model.load_state_dict(

            checkpoint["model_state_dict"]

        )

        model.to(self.device)

        model.eval()

        return model