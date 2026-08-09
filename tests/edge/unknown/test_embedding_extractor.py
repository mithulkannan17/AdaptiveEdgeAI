"""
Tests for EmbeddingExtractor.
"""

import torch
import torch.nn as nn

from edge.unknown.embedding_extractor import (
    EmbeddingExtractor,
)


class DummyMobileNet(nn.Module):

    def __init__(self):

        super().__init__()

        self.model = nn.Module()

        self.model.features = nn.Sequential(

            nn.Conv2d(
                3,
                8,
                kernel_size=3,
                padding=1
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


class DummyAuraCNN(nn.Module):

    def __init__(self):

        super().__init__()

        self.features = nn.Sequential(

            nn.Conv2d(
                1,
                8,
                kernel_size=3,
                padding=1
            ),

            nn.ReLU(),

        )

        self.pool = (
            nn.AdaptiveAvgPool2d(
                (1, 1)
            )
        )

    def forward(self, x):

        x = self.features(x)

        x = self.pool(x)

        return x.flatten(1)


class TestEmbeddingExtractor:

    def test_mobilenet_embedding(self):

        model = DummyMobileNet()

        extractor = EmbeddingExtractor(

            model=model,

            device=torch.device("cpu")

        )

        spectrogram = torch.randn(
            1,
            1,
            128,
            157
        )

        embedding = extractor.extract(
            spectrogram
        )

        assert isinstance(
            embedding,
            torch.Tensor
        )

        assert embedding.ndim == 1

        assert embedding.shape[0] == 8

    def test_aura_cnn_embedding(self):

        model = DummyAuraCNN()

        extractor = EmbeddingExtractor(

            model=model,

            device=torch.device("cpu")

        )

        spectrogram = torch.randn(
            1,
            1,
            128,
            157
        )

        embedding = extractor.extract(
            spectrogram
        )

        assert isinstance(
            embedding,
            torch.Tensor
        )

        assert embedding.ndim == 1

        assert embedding.shape[0] == 8

    def test_numpy_is_not_required(self):

        model = DummyAuraCNN()

        extractor = EmbeddingExtractor(

            model=model,

            device=torch.device("cpu")

        )

        spectrogram = torch.randn(
            1,
            1,
            128,
            157
        )

        embedding = extractor.extract(
            spectrogram
        )

        assert embedding.device.type == "cpu"

    def test_batch_dimension_is_removed(self):

        model = DummyAuraCNN()

        extractor = EmbeddingExtractor(

            model=model,

            device=torch.device("cpu")

        )

        spectrogram = torch.randn(
            1,
            1,
            128,
            157
        )

        embedding = extractor.extract(
            spectrogram
        )

        assert embedding.ndim == 1

    def test_unsupported_model_raises_error(self):

        class UnsupportedModel(nn.Module):

            def forward(self, x):

                return x

        model = UnsupportedModel()

        extractor = EmbeddingExtractor(

            model=model,

            device=torch.device("cpu")

        )

        spectrogram = torch.randn(
            1,
            1,
            128,
            157
        )

        try:

            extractor.extract(
                spectrogram
            )

            assert False

        except TypeError as exc:

            assert (
                "Unsupported model architecture"
                in str(exc)
            )