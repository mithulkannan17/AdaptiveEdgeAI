"""
Tests for UnknownBuffer.
"""

import torch
import pytest

from edge.unknown.unknown_buffer import (
    UnknownBuffer,
)


class TestUnknownBuffer:

    def test_empty_buffer(self):

        buffer = UnknownBuffer()

        assert buffer.size() == 0

        assert not buffer.is_ready(1)

    def test_add_sample(self):

        buffer = UnknownBuffer()

        embedding = torch.randn(128)

        buffer.add(
            embedding=embedding,
            predicted_class=3,
            confidence=0.42,
        )

        assert buffer.size() == 1

    def test_embedding_storage(self):

        buffer = UnknownBuffer()

        embedding = torch.randn(128)

        buffer.add(
            embedding=embedding,
            predicted_class=2,
            confidence=0.50,
        )

        stored = buffer.embeddings()

        assert stored.shape == (1, 128)

    def test_buffer_readiness(self):

        buffer = UnknownBuffer()

        for _ in range(3):

            buffer.add(
                embedding=torch.randn(128),
                predicted_class=1,
                confidence=0.40,
            )

        assert not buffer.is_ready(4)

        assert buffer.is_ready(3)

    def test_max_size_fifo(self):

        buffer = UnknownBuffer(
            max_size=3
        )

        for index in range(5):

            buffer.add(
                embedding=torch.full(
                    (4,),
                    float(index)
                ),
                predicted_class=index,
                confidence=0.5,
            )

        assert buffer.size() == 3

        embeddings = buffer.embeddings()

        assert torch.equal(
            embeddings[0],
            torch.full(
                (4,),
                2.0
            )
        )

    def test_confidence_is_clamped(self):

        buffer = UnknownBuffer()

        buffer.add(
            embedding=torch.randn(8),
            predicted_class=1,
            confidence=2.0,
        )

        assert (
            buffer.get_samples()[0].confidence
            == 1.0
        )

        buffer.add(
            embedding=torch.randn(8),
            predicted_class=1,
            confidence=-1.0,
        )

        assert (
            buffer.get_samples()[1].confidence
            == 0.0
        )

    def test_invalid_embedding(self):

        buffer = UnknownBuffer()

        with pytest.raises(ValueError):

            buffer.add(
                embedding=None,
                predicted_class=1,
                confidence=0.5,
            )

    def test_invalid_embedding_dimension(self):

        buffer = UnknownBuffer()

        with pytest.raises(ValueError):

            buffer.add(
                embedding=torch.randn(
                    1,
                    128
                ),
                predicted_class=1,
                confidence=0.5,
            )

    def test_get_samples_returns_copy(self):

        buffer = UnknownBuffer()

        buffer.add(
            embedding=torch.randn(8),
            predicted_class=1,
            confidence=0.5,
        )

        samples = buffer.get_samples()

        samples.clear()

        assert buffer.size() == 1

    def test_clear(self):

        buffer = UnknownBuffer()

        buffer.add(
            embedding=torch.randn(8),
            predicted_class=1,
            confidence=0.5,
        )

        buffer.clear()

        assert buffer.size() == 0

    def test_pop_batch(self):

        buffer = UnknownBuffer()

        for _ in range(5):

            buffer.add(
                embedding=torch.randn(8),
                predicted_class=1,
                confidence=0.5,
            )

        batch = buffer.pop_batch(2)

        assert len(batch) == 2

        assert buffer.size() == 3

    def test_invalid_batch_size(self):

        buffer = UnknownBuffer()

        with pytest.raises(ValueError):

            buffer.pop_batch(0)

    def test_sample_serialization(self):

        buffer = UnknownBuffer()

        buffer.add(
            embedding=torch.randn(8),
            predicted_class=4,
            confidence=0.72,
            audio_path="sample.wav",
            timestamp=123.0,
        )

        sample = buffer.get_samples()[0]

        data = sample.to_dict()

        assert data["predicted_class"] == 4

        assert data["confidence"] == 0.72

        assert data["audio_path"] == "sample.wav"

        assert data["timestamp"] == 123.0

        assert "embedding" not in data