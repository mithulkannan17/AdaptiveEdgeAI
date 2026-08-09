"""
Model Loader

Loads the configured trained deep learning model for inference.

The checkpoint can either be supplied explicitly or resolved
automatically from the project configuration.
"""

from __future__ import annotations

from pathlib import Path

import torch

from managers.config_manager import ConfigManager
from models.model_factory import ModelFactory


class ModelLoader:
    """
    Loads a trained model for inference.

    If checkpoint_path is provided, that checkpoint is used.

    Otherwise the checkpoint is resolved from:

        training_config.checkpoint.directory
        /
        model_name
        /
        best_model.pth
    """

    def __init__(
        self,
        device: torch.device,
        checkpoint_path: str | Path | None = None,
    ):
        self.device = device

        config = ConfigManager()

        self.training_config = config.training()

        self.model_config = config.model()

        self.model_name = self.model_config["name"]

        # --------------------------------------------------
        # Checkpoint
        # --------------------------------------------------

        if checkpoint_path is not None:

            self.checkpoint_path = Path(
                checkpoint_path
            )

        else:

            self.checkpoint_path = (

                Path(
                    self.training_config[
                        "checkpoint"
                    ][
                        "directory"
                    ]
                )

                / self.model_name

                / "best_model.pth"

            )

    # ======================================================
    # Load Model
    # ======================================================

    def load(
        self,
    ) -> torch.nn.Module:
        """
        Load the trained model.

        Returns
        -------
        torch.nn.Module
            Model ready for inference.
        """

        if not self.checkpoint_path.exists():

            raise FileNotFoundError(

                "Checkpoint not found:\n"
                f"{self.checkpoint_path}"

            )

        # --------------------------------------------------
        # Build architecture from configuration
        # --------------------------------------------------

        model = (

            ModelFactory

            .build(
                self.model_config
            )

            .to(self.device)

        )

        # --------------------------------------------------
        # Load checkpoint
        # --------------------------------------------------

        checkpoint = torch.load(

            self.checkpoint_path,

            map_location=self.device

        )

        if "model_state_dict" not in checkpoint:

            raise KeyError(

                "Checkpoint does not contain "
                "'model_state_dict'."

            )

        model.load_state_dict(

            checkpoint[
                "model_state_dict"
            ]

        )

        model.eval()

        return model

    # ======================================================
    # Information
    # ======================================================

    def get_model_name(
        self,
    ) -> str:
        """
        Return the configured model name.
        """

        return self.model_name

    def get_checkpoint_path(
        self,
    ) -> Path:
        """
        Return the checkpoint path being used.
        """

        return self.checkpoint_path