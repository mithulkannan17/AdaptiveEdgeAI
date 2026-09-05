"""
Embedding Extractor

Extracts intermediate feature representations from
the trained classification model for unknown-sound
discovery and clustering.
"""

from __future__ import annotations

import torch
import torch.nn as nn


class EmbeddingExtractor:
    """
    Extracts intermediate feature representations from
    a trained classification model.

    Supports:
        - MobileNetV3-Small
        - AuraCNN
    """

    def __init__(
        self,
        model: nn.Module,
        device: torch.device,
    ):
        self.model = model
        self.device = device

        self.model.to(self.device)
        self.model.eval()

    def extract(
        self,
        spectrogram: torch.Tensor,
    ) -> torch.Tensor:
        """
        Extract an embedding from a spectrogram.

        Accepts either:

            [128, 157]
            [1, 128, 157]
            [1, 1, 128, 157]

        Returns:

            [embedding_dimension]
        """

        spectrogram = spectrogram.to(
            self.device
        )

        with torch.no_grad():

            embedding = self._extract_features(
                spectrogram
            )

        if embedding.ndim > 2:

            embedding = torch.flatten(
                embedding,
                start_dim=1
            )

        return (
            embedding
            .squeeze(0)
            .detach()
            .cpu()
        )

    def _prepare_mobilenet_input(
        self,
        spectrogram: torch.Tensor,
    ) -> torch.Tensor:
        """
        Convert a model-ready mel spectrogram into
        MobileNet-compatible 4-D image format:

            [N, C, H, W]

        Expected final shape:

            [1, 3, 224, 224]
        """

        x = spectrogram

        # --------------------------------------------------
        # Remove unnecessary dimensions
        # --------------------------------------------------

        if x.ndim == 2:

            # [H, W]
            x = x.unsqueeze(0).unsqueeze(0)

        elif x.ndim == 3:

            # [C, H, W]
            x = x.unsqueeze(0)

        elif x.ndim != 4:

            raise ValueError(
                "Unsupported spectrogram shape: "
                f"{tuple(x.shape)}. "
                "Expected [H,W], [C,H,W], "
                "or [N,C,H,W]."
            )

        # --------------------------------------------------
        # Channel normalization
        # --------------------------------------------------

        channels = x.shape[1]

        if channels == 1:

            # Mel spectrogram is single-channel.
            # MobileNet expects RGB-style 3 channels.
            x = x.repeat(
                1,
                3,
                1,
                1
            )

        elif channels != 3:

            raise ValueError(
                "Unsupported spectrogram channel count: "
                f"{channels}. Expected 1 or 3."
            )

        # --------------------------------------------------
        # Resize to MobileNet input dimensions
        # --------------------------------------------------

        x = torch.nn.functional.interpolate(
            x,
            size=(224, 224),
            mode="bilinear",
            align_corners=False,
        )

        return x

    def _extract_features(
        self,
        spectrogram: torch.Tensor,
    ) -> torch.Tensor:
        """
        Extract intermediate features according to
        the model architecture.
        """

        # ==================================================
        # MobileNetV3-Small
        # ==================================================

        if hasattr(self.model, "model"):

            backbone = self.model.model

            x = self._prepare_mobilenet_input(
                spectrogram
            )

            x = backbone.features(x)

            x = backbone.avgpool(x)

            return x

        # ==================================================
        # AuraCNN
        # ==================================================

        if hasattr(self.model, "features"):

            x = spectrogram

            # AuraCNN expects channel dimension.
            if x.ndim == 2:

                x = x.unsqueeze(0).unsqueeze(0)

            elif x.ndim == 3:

                x = x.unsqueeze(0)

            elif x.ndim != 4:

                raise ValueError(
                    "Unsupported spectrogram shape: "
                    f"{tuple(x.shape)}"
                )

            x = self.model.features(x)

            x = self.model.pool(x)

            return x

        # ==================================================
        # Unsupported architecture
        # ==================================================

        raise TypeError(
            "Unsupported model architecture. "
            "Expected a model containing either "
            "'model' or 'features'."
        )