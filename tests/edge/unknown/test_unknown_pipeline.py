"""
End-to-End Synthetic Test for Unknown Sound Discovery.
"""

import numpy as np
import torch
import torch.nn as nn

from edge.unknown import (
    UnknownDiscoveryManager,
)


class DummyModel(nn.Module):

    def __init__(self):

        super().__init__()

        self.model = nn.Module()

        self.model.features = nn.Sequential(

            nn.Conv2d(
                3,
                16,
                kernel_size=3,
                padding=1,
            ),

            nn.ReLU(),

        )

        self.model.avgpool = (
            nn.AdaptiveAvgPool2d(
                (1, 1)
            )
        )

    def forward(self, x):

        x = self.model.features(x)

        x = self.model.avgpool(x)

        return x.flatten(1)


def test_unknown_discovery_end_to_end():

    model = DummyModel()

    manager = UnknownDiscoveryManager(

        model=model,

        device=torch.device("cpu"),

        confidence_threshold=0.60,

        margin_threshold=0.15,

        buffer_size=20,

        clustering_batch_size=3,

    )

    unknown_probabilities = np.array([

        0.40,
        0.35,
        0.05,
        0.04,
        0.04,
        0.03,
        0.03,
        0.02,
        0.02,
        0.02,

    ])

    spectrogram = torch.randn(

        1,
        1,
        128,
        157,

    )

    results = []

    for index in range(3):

        result = manager.process(

            probabilities=(
                unknown_probabilities
            ),

            spectrogram=spectrogram,

            audio_path=(
                f"unknown_{index}.wav"
            ),

        )

        results.append(result)

    assert all(

        result.decision.is_unknown

        for result in results

    )

    assert manager.buffer_size() == 3

    final_result = results[-1]

    assert (
        final_result.clustering_triggered
        is True
    )

    assert (
        final_result.cluster_result
        is not None
    )

    assert (
        final_result.cluster_result.sample_count
        == 3
    )

    assert isinstance(

        final_result.to_dict(),

        dict

    )