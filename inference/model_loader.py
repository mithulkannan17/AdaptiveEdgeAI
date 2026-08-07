"""
Model Loader

Loads trained deep learning models for inference.
"""

from pathlib import Path

import torch

from managers.config_manager import ConfigManager
from models.model_factory import ModelFactory


class ModelLoader:
    """
    Loads the configured trained model for inference.
    """

    def __init__(

        self,

        device: torch.device,

    ):

        config = ConfigManager()

        self.training_config = config.training()

        self.model_config = config.model()

        self.model_name = self.model_config["name"]

        self.device = device

        self.checkpoint_path = (

            Path(

                self.training_config["checkpoint"]["directory"]

            )

            / self.model_name

            / "best_model.pth"

        )

    def load(self) -> torch.nn.Module:
        """
        Loads the configured trained model.

        Returns
        -------
        torch.nn.Module
            Model ready for inference.
        """

        if not self.checkpoint_path.exists():

            raise FileNotFoundError(

                f"Checkpoint not found:\n{self.checkpoint_path}"

            )

        model = (

            ModelFactory

            .build(self.model_config)

            .to(self.device)

        )

        checkpoint = torch.load(

            self.checkpoint_path,

            map_location=self.device

        )

        model.load_state_dict(

            checkpoint["model_state_dict"]

        )

        model.eval()

        return model