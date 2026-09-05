"""
Model Loader

Loads the configured trained deep learning model for inference.

The checkpoint can either be supplied explicitly or resolved
automatically from the project configuration.

Supported explicit model checkpoints include:

    models/checkpoints/aura_cnn/best_model.pth

    models/checkpoints/mobilenet_v3_small/best_model.pth

When an explicit checkpoint is supplied from a temporary or
unknown directory, the configured project model is used instead
of treating the temporary directory name as a model name.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import torch

from managers.config_manager import ConfigManager
from models.model_factory import ModelFactory


class ModelLoader:
    """
    Loads a trained model for inference.

    Model selection rules
    ---------------------

    Explicit checkpoint
        If the checkpoint is located inside a recognized model
        directory, that model architecture is selected.

        Example:

            .../aura_cnn/best_model.pth

        selects:

            aura_cnn

        If the parent directory is not recognized, the configured
        project model is used.

    Default checkpoint
        When no checkpoint is supplied, the model configured in
        the project configuration is used.
    """

    # ------------------------------------------------------
    # Known production model directories
    # ------------------------------------------------------

    KNOWN_MODELS = {
        "aura_cnn",
        "mobilenet_v3_small",
    }

    def __init__(
        self,
        device: torch.device,
        checkpoint_path: str | Path | None = None,
    ):
        self.device = device

        config = ConfigManager()

        self.training_config = (
            config.training()
        )

        self.model_config = (
            config.model()
        )

        self.configured_model_name = (
            self.model_config["name"]
        )

        self.explicit_checkpoint = (
            checkpoint_path is not None
        )

        # --------------------------------------------------
        # Explicit checkpoint
        # --------------------------------------------------

        if checkpoint_path is not None:

            self.checkpoint_path = Path(
                checkpoint_path
            )

            checkpoint_model_name = (
                self.checkpoint_path
                .parent
                .name
            )

            # --------------------------------------------------
            # Only use the directory name when it represents
            # a real production model.
            #
            # This prevents temporary pytest directories such
            # as:
            #
            # test_predictor_unknown_discove0
            #
            # from being interpreted as model architectures.
            # --------------------------------------------------

            if (
                checkpoint_model_name
                in self.KNOWN_MODELS
            ):

                self.model_name = (
                    checkpoint_model_name
                )

            else:

                self.model_name = (
                    self.configured_model_name
                )

        # --------------------------------------------------
        # Automatically resolved checkpoint
        # --------------------------------------------------

        else:

            self.model_name = (
                self.configured_model_name
            )

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
    # Model Configuration
    # ======================================================

    def _get_model_config(
        self,
    ) -> dict:
        """
        Return the model configuration used to construct
        the architecture.
        """

        model_config = deepcopy(
            self.model_config
        )

        model_config["name"] = (
            self.model_name
        )

        return model_config

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

        # --------------------------------------------------
        # Validate checkpoint
        # --------------------------------------------------

        if not self.checkpoint_path.exists():

            raise FileNotFoundError(

                "Checkpoint not found:\n"
                f"{self.checkpoint_path}"

            )

        # --------------------------------------------------
        # Build architecture
        # --------------------------------------------------

        model_config = (
            self._get_model_config()
        )

        model = (

            ModelFactory

            .build(
                model_config
            )

            .to(self.device)

        )

        # --------------------------------------------------
        # Load checkpoint
        # --------------------------------------------------

        checkpoint = torch.load(

            self.checkpoint_path,

            map_location=self.device,

        )

        # --------------------------------------------------
        # Validate checkpoint
        # --------------------------------------------------

        if not isinstance(
            checkpoint,
            dict,
        ):

            raise TypeError(

                "Checkpoint must contain a "
                "dictionary-like object."

            )

        if (
            "model_state_dict"
            not in checkpoint
        ):

            raise KeyError(

                "Checkpoint does not contain "
                "'model_state_dict'."

            )

        state_dict = (
            checkpoint[
                "model_state_dict"
            ]
        )

        # --------------------------------------------------
        # Load weights
        # --------------------------------------------------

        try:

            model.load_state_dict(
                state_dict
            )

        except RuntimeError as exc:

            raise RuntimeError(

                "Failed to load checkpoint.\n\n"

                f"Checkpoint:\n"
                f"{self.checkpoint_path}\n\n"

                f"Model architecture:\n"
                f"{self.model_name}\n\n"

                "The checkpoint weights do not match "
                "the selected model architecture.\n\n"

                f"Original error:\n{exc}"

            ) from exc

        # --------------------------------------------------
        # Evaluation mode
        # --------------------------------------------------

        model.eval()

        return model

    # ======================================================
    # Information
    # ======================================================

    def get_model_name(
        self,
    ) -> str:
        """
        Return the model architecture associated with
        the checkpoint.
        """

        return self.model_name

    def get_checkpoint_path(
        self,
    ) -> Path:
        """
        Return the checkpoint path being used.
        """

        return self.checkpoint_path