"""
Embedding Extractor

Extracts feature embeddings from trained environmental
sound classification models.

These embeddings are used for unknown-sound clustering.
"""

from __future__ import annotations

import torch
import torch.nn as nn


class EmbeddingExtractor:
    """
    Extracts intermediate feature representations from
    a trained classification model.

    The extractor is intentionally model-agnostic where
    possible, but currently supports the project's
    MobileNetV3-Small and AuraCNN architectures.
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

        Parameters
        ----------
        spectrogram:
            Model-ready spectrogram.

        Returns
        -------
        torch.Tensor
            One-dimensional feature embedding.
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

        return embedding.squeeze(0).detach().cpu()

    def _extract_features(
        self,
        spectrogram: torch.Tensor,
    ) -> torch.Tensor:
        """
        Extract intermediate features according to
        the model architecture.
        """

        # --------------------------------------------------
        # MobileNetV3-Small
        # --------------------------------------------------

        if hasattr(self.model, "model"):

            backbone = self.model.model

            x = spectrogram

            # Convert 1-channel spectrogram → 3 channels
            if x.shape[1] == 1:

                x = x.repeat(
                    1,
                    3,
                    1,
                    1
                )

            # Match MobileNet input dimensions
            x = torch.nn.functional.interpolate(
                x,
                size=(224, 224),
                mode="bilinear",
                align_corners=False,
            )

            x = backbone.features(x)

            x = backbone.avgpool(x)

            return x

        # --------------------------------------------------
        # AuraCNN
        # --------------------------------------------------

        if hasattr(self.model, "features"):

            x = self.model.features(
                spectrogram
            )

            x = self.model.pool(x)

            return x

        raise TypeError(
            "Unsupported model architecture. "
            "Expected a model containing either "
            "'model' or 'features'."
        )