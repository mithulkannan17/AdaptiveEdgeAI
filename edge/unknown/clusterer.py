"""
Unknown Sound Clusterer

Groups unknown acoustic embeddings into previously
unseen sound clusters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
import torch
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler


@dataclass
class ClusterResult:
    """
    Result produced by the unknown-sound clusterer.
    """

    labels: List[int]

    number_of_clusters: int

    number_of_noise_samples: int

    sample_count: int

    def to_dict(self) -> dict:
        """
        Convert result into a serializable dictionary.
        """

        return {
            "labels": self.labels,

            "number_of_clusters":
                self.number_of_clusters,

            "number_of_noise_samples":
                self.number_of_noise_samples,

            "sample_count":
                self.sample_count,
        }


class UnknownClusterer:
    """
    DBSCAN-based clustering engine for unknown
    environmental sound embeddings.

    Cluster IDs are local identifiers only.

    For example:

        0 → UNKNOWN_CLUSTER_0
        1 → UNKNOWN_CLUSTER_1

    They must NOT automatically be interpreted
    as semantic sound classes.
    """

    def __init__(
        self,
        eps: float = 0.8,
        min_samples: int = 3,
        normalize: bool = True,
    ):

        if eps <= 0:

            raise ValueError(
                "eps must be greater than zero."
            )

        if min_samples <= 0:

            raise ValueError(
                "min_samples must be greater than zero."
            )

        self.eps = eps

        self.min_samples = min_samples

        self.normalize = normalize

    def _prepare_embeddings(
        self,
        embeddings: torch.Tensor | np.ndarray,
    ) -> np.ndarray:
        """
        Convert embeddings into a NumPy matrix.
        """

        if isinstance(
            embeddings,
            torch.Tensor
        ):

            embeddings = embeddings.detach().cpu().numpy()

        else:

            embeddings = np.asarray(
                embeddings,
                dtype=np.float32
            )

        if embeddings.ndim != 2:

            raise ValueError(
                "Embeddings must have shape "
                "[N, embedding_dimension]."
            )

        if embeddings.shape[0] == 0:

            raise ValueError(
                "At least one embedding is required."
            )

        if not np.isfinite(
            embeddings
        ).all():

            raise ValueError(
                "Embeddings contain NaN or "
                "infinite values."
            )

        if self.normalize:

            embeddings = StandardScaler().fit_transform(
                embeddings
            )

        return embeddings

    def cluster(
        self,
        embeddings: torch.Tensor | np.ndarray,
    ) -> ClusterResult:
        """
        Cluster unknown sound embeddings.

        Parameters
        ----------
        embeddings:
            Matrix with shape [N, D].

        Returns
        -------
        ClusterResult
        """

        embeddings = self._prepare_embeddings(
            embeddings
        )

        if embeddings.shape[0] < self.min_samples:

            return ClusterResult(

                labels=[-1] * embeddings.shape[0],

                number_of_clusters=0,

                number_of_noise_samples=(
                    embeddings.shape[0]
                ),

                sample_count=(
                    embeddings.shape[0]
                ),

            )

        model = DBSCAN(

            eps=self.eps,

            min_samples=self.min_samples,

            metric="euclidean",

        )

        labels = model.fit_predict(
            embeddings
        )

        labels = labels.tolist()

        unique_labels = set(labels)

        cluster_labels = {

            label

            for label in unique_labels

            if label != -1

        }

        noise_count = labels.count(-1)

        return ClusterResult(

            labels=labels,

            number_of_clusters=len(
                cluster_labels
            ),

            number_of_noise_samples=(
                noise_count
            ),

            sample_count=len(
                labels
            ),

        )