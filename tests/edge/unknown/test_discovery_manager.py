"""
Tests for UnknownDiscoveryManager.
"""

import numpy as np
import torch
import torch.nn as nn

from edge.unknown.discovery_manager import (
    UnknownDiscoveryManager,
)


class DummyModel(nn.Module):

    def __init__(self):

        super().__init__()

        self.model = nn.Module()

        self.model.features = nn.Sequential(

            nn.Conv2d(
                3,
                8,
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


class TestUnknownDiscoveryManager:

    def create_manager(
        self,
        clustering_batch_size=3,
    ):

        model = DummyModel()

        return UnknownDiscoveryManager(

            model=model,

            device=torch.device("cpu"),

            confidence_threshold=0.60,

            margin_threshold=0.15,

            buffer_size=20,

            clustering_batch_size=(
                clustering_batch_size
            ),

        )

    def test_known_prediction_is_not_buffered(self):

        manager = self.create_manager()

        probabilities = np.array([

            0.90,
            0.02,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,
            0.01,

        ])

        spectrogram = torch.randn(
            1,
            1,
            128,
            157,
        )

        result = manager.process(

            probabilities=probabilities,

            spectrogram=spectrogram,

        )

        assert result.decision.is_unknown is False

        assert result.buffered is False

        assert manager.buffer_size() == 0

    def test_unknown_prediction_is_buffered(self):

        manager = self.create_manager()

        probabilities = np.array([

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

        result = manager.process(

            probabilities=probabilities,

            spectrogram=spectrogram,

        )

        assert result.decision.is_unknown is True

        assert result.buffered is True

        assert manager.buffer_size() == 1

    def test_clustering_is_triggered(self):

        manager = self.create_manager(

            clustering_batch_size=3

        )

        probabilities = np.array([

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

        for _ in range(3):

            result = manager.process(

                probabilities=probabilities,

                spectrogram=torch.randn(
                    1,
                    1,
                    128,
                    157,
                ),

            )

        assert (
            result.clustering_triggered
            is True
        )

        assert (
            result.cluster_result
            is not None
        )

    def test_clustering_not_triggered_early(self):

        manager = self.create_manager(

            clustering_batch_size=5

        )

        probabilities = np.array([

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

        result = manager.process(

            probabilities=probabilities,

            spectrogram=torch.randn(
                1,
                1,
                128,
                157,
            ),

        )

        assert (
            result.clustering_triggered
            is False
        )

        assert (
            result.cluster_result
            is None
        )

    def test_clear(self):

        manager = self.create_manager()

        probabilities = np.array([

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

        manager.process(

            probabilities=probabilities,

            spectrogram=torch.randn(
                1,
                1,
                128,
                157,
            ),

        )

        assert manager.buffer_size() == 1

        manager.clear()

        assert manager.buffer_size() == 0

    def test_result_serialization(self):

        manager = self.create_manager()

        probabilities = np.array([

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

        result = manager.process(

            probabilities=probabilities,

            spectrogram=torch.randn(
                1,
                1,
                128,
                157,
            ),

        )

        data = result.to_dict()

        assert isinstance(
            data,
            dict
        )

        assert (
            "decision"
            in data
        )

        assert (
            "buffered"
            in data
        )

        assert (
            "buffer_size"
            in data
        )

        assert (
            "clustering_triggered"
            in data
        )