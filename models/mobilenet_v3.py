"""
MobileNetV3-Small

Production implementation for environmental sound classification.
"""

from __future__ import annotations

import torch.nn as nn
import torch.nn.functional as F

from torchvision.models import (
    MobileNet_V3_Small_Weights,
    mobilenet_v3_small,
)


class MobileNetV3Small(nn.Module):
    """
    MobileNetV3-Small adapted for Environmental Sound Classification.
    """

    def __init__(
        self,
        input_channels: int = 1,
        num_classes: int = 14,
        dropout: float = 0.3,
        pretrained: bool = True,
    ):

        super().__init__()

        # These parameters are accepted to maintain a common
        # interface across all models.
        self.input_channels = input_channels
        self.dropout = dropout

        weights = (
            MobileNet_V3_Small_Weights.DEFAULT
            if pretrained
            else None
        )

        self.model = mobilenet_v3_small(
            weights=weights
        )

        in_features = self.model.classifier[-1].in_features

        self.model.classifier[-1] = nn.Linear(
            in_features,
            num_classes
        )

    def forward(self, x):

        # Convert spectrogram from 1 channel → 3 channels
        if x.shape[1] == 1:
            x = x.repeat(1, 3, 1, 1)

        # Resize to ImageNet input size
        x = F.interpolate(
            x,
            size=(224, 224),
            mode="bilinear",
            align_corners=False,
        )

        return self.model(x)