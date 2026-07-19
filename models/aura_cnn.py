"""
AuraCNN

Production CNN for Environmental Sound Classification.
Optimized version of the original architecture.
"""

import torch
import torch.nn as nn

from managers.config_manager import ConfigManager


class ConvBlock(nn.Module):

    def __init__(self, in_channels, out_channels):

        super().__init__()

        self.block = nn.Sequential(

            nn.Conv2d(
                in_channels,
                out_channels,
                kernel_size=3,
                padding=1,
                bias=False
            ),

            nn.BatchNorm2d(out_channels),

            nn.ReLU(inplace=True),

            nn.Conv2d(
                out_channels,
                out_channels,
                kernel_size=3,
                padding=1,
                bias=False
            ),

            nn.BatchNorm2d(out_channels),

            nn.ReLU(inplace=True),

            nn.MaxPool2d(kernel_size=2)

        )

    def forward(self, x):

        return self.block(x)


class AuraCNN(nn.Module):

    def __init__(self):

        super().__init__()

        cfg = ConfigManager().model()

        in_channels = cfg["input_channels"]

        num_classes = cfg["num_classes"]

        dropout = cfg["dropout"]

        # ------------------------------
        # Feature Extractor
        # ------------------------------

        self.features = nn.Sequential(

            ConvBlock(in_channels, 32),

            ConvBlock(32, 64),

            ConvBlock(64, 128),

            ConvBlock(128, 256)

        )

        # ------------------------------
        # Global Pooling
        # ------------------------------

        self.pool = nn.AdaptiveAvgPool2d((1, 1))

        # ------------------------------
        # Classifier
        # ------------------------------

        self.classifier = nn.Sequential(

            nn.Flatten(),

            nn.Dropout(dropout),

            nn.Linear(256, 128),

            nn.ReLU(inplace=True),

            nn.Dropout(dropout),

            nn.Linear(128, num_classes)

        )

        # Initialize weights
        self._initialize_weights()

    def _initialize_weights(self):

        for module in self.modules():

            if isinstance(module, nn.Conv2d):

                nn.init.kaiming_normal_(

                    module.weight,

                    mode="fan_out",

                    nonlinearity="relu"

                )

                if module.bias is not None:

                    nn.init.constant_(module.bias, 0)

            elif isinstance(module, nn.BatchNorm2d):

                nn.init.constant_(module.weight, 1)

                nn.init.constant_(module.bias, 0)

            elif isinstance(module, nn.Linear):

                nn.init.normal_(

                    module.weight,

                    mean=0.0,

                    std=0.01

                )

                nn.init.constant_(module.bias, 0)

    def forward(self, x):

        x = self.features(x)

        x = self.pool(x)

        x = self.classifier(x)

        return x