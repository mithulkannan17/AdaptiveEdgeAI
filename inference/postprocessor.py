"""
Postprocessor

Converts raw model outputs into human-readable predictions.
"""

from __future__ import annotations

from typing import List

import torch
import torch.nn.functional as F

from inference.types import PredictionResult
from training.label_encoder import LabelEncoder


class PostProcessor:
    """
    Converts model logits into prediction results.
    """

    def __init__(self):

        self.encoder = LabelEncoder()

    def process(
        self,
        logits: torch.Tensor,
        top_k: int = 5,
        inference_time_ms: float = 0.0,
    ) -> PredictionResult:
        """
        Process model output.

        Parameters
        ----------
        logits:
            Raw output from the neural network.

        top_k:
            Number of highest confidence predictions.

        inference_time_ms:
            Model inference latency.

        Returns
        -------
        PredictionResult
        """

        probabilities = F.softmax(logits, dim=1)

        confidence, predicted = torch.max(
            probabilities,
            dim=1
        )

        predicted_index = predicted.item()

        predicted_label = self.encoder.decode(
            predicted_index
        )

        values, indices = torch.topk(
            probabilities,
            k=min(top_k, probabilities.shape[1]),
            dim=1
        )

        top_predictions: List[tuple[str, float]] = []

        for score, index in zip(
            values[0],
            indices[0]
        ):

            top_predictions.append(

                (
                    self.encoder.decode(index.item()),
                    float(score.item())
                )

            )

        return PredictionResult(

            label=predicted_label,

            class_id=predicted_index,

            confidence=float(confidence.item()),

            top_k=top_predictions,

            inference_time_ms=inference_time_ms

        )