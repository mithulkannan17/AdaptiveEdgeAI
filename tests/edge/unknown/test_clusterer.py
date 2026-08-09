"""
Tests for UnknownClusterer.
"""

import numpy as np
import pytest
import torch

from edge.unknown.clusterer import (
    UnknownClusterer,
)


class TestUnknownClusterer:

    def test_two_distinct_clusters(self):

        embeddings = np.array([

            [0.0, 0.0],
            [0.1, 0.1],
            [0.2, 0.0],

            [10.0, 10.0],
            [10.1, 10.1],
            [9.9, 10.0],

        ])

        clusterer = UnknownClusterer(

            eps=0.8,

            min_samples=2,

        )

        result = clusterer.cluster(
            embeddings
        )

        assert (
            result.number_of_clusters
            == 2
        )

        assert (
            result.sample_count
            == 6
        )

        assert (
            result.number_of_noise_samples
            == 0
        )

    def test_noise_detection(self):

        embeddings = np.array([

            [0.0, 0.0],
            [0.1, 0.1],
            [0.2, 0.0],

            [10.0, 10.0],

        ])

        clusterer = UnknownClusterer(

            eps=0.8,

            min_samples=3,

        )

        result = clusterer.cluster(
            embeddings
        )

        assert (
            result.number_of_clusters
            >= 1
        )

        assert (
            result.number_of_noise_samples
            >= 1
        )

        assert -1 in result.labels

    def test_torch_tensor_input(self):

        embeddings = torch.tensor([

            [0.0, 0.0],
            [0.1, 0.1],
            [0.2, 0.0],

            [10.0, 10.0],
            [10.1, 10.1],
            [9.9, 10.0],

        ])

        clusterer = UnknownClusterer(

            eps=0.8,

            min_samples=2,

        )

        result = clusterer.cluster(
            embeddings
        )

        assert (
            result.number_of_clusters
            == 2
        )

    def test_single_sample(self):

        embeddings = np.array([

            [1.0, 2.0, 3.0]

        ])

        clusterer = UnknownClusterer(

            eps=0.8,

            min_samples=3,

        )

        result = clusterer.cluster(
            embeddings
        )

        assert (
            result.number_of_clusters
            == 0
        )

        assert (
            result.number_of_noise_samples
            == 1
        )

        assert result.labels == [-1]

    def test_empty_embeddings(self):

        clusterer = UnknownClusterer()

        with pytest.raises(ValueError):

            clusterer.cluster(
                np.empty(
                    (0, 128)
                )
            )

    def test_invalid_dimensions(self):

        clusterer = UnknownClusterer()

        with pytest.raises(ValueError):

            clusterer.cluster(
                np.random.randn(128)
            )

    def test_nan_embeddings(self):

        clusterer = UnknownClusterer()

        embeddings = np.array([

            [0.0, 0.0],

            [np.nan, 1.0],

        ])

        with pytest.raises(ValueError):

            clusterer.cluster(
                embeddings
            )

    def test_infinite_embeddings(self):

        clusterer = UnknownClusterer()

        embeddings = np.array([

            [0.0, 0.0],

            [np.inf, 1.0],

        ])

        with pytest.raises(ValueError):

            clusterer.cluster(
                embeddings
            )

    def test_cluster_result_serialization(self):

        embeddings = np.array([

            [0.0, 0.0],
            [0.1, 0.1],
            [0.2, 0.0],

        ])

        clusterer = UnknownClusterer(

            eps=0.8,

            min_samples=2,

        )

        result = clusterer.cluster(
            embeddings
        )

        data = result.to_dict()

        assert isinstance(
            data,
            dict
        )

        assert (
            "labels"
            in data
        )

        assert (
            "number_of_clusters"
            in data
        )

        assert (
            "number_of_noise_samples"
            in data
        )

    def test_invalid_eps(self):

        with pytest.raises(ValueError):

            UnknownClusterer(
                eps=0
            )

    def test_invalid_min_samples(self):

        with pytest.raises(ValueError):

            UnknownClusterer(
                min_samples=0
            )