"""
Predictor

Production inference interface.
"""

from __future__ import annotations

import time

import numpy as np
import torch

from inference.device import DeviceManager
from inference.model_loader import ModelLoader
from inference.postprocessor import PostProcessor
from inference.types import PredictionResult


class Predictor:
    """
    Production inference interface.

    Loads the configured model once and performs
    fast inference on spectrograms.
    """

    def __init__(self):

        self.device = DeviceManager.get_device()

        self.model = ModelLoader(

            self.device

        ).load()

        self.postprocessor = PostProcessor()

    def predict_spectrogram(

        self,

        spectrogram: np.ndarray | torch.Tensor,

        top_k: int = 5,

    ) -> PredictionResult:
        """
        Predict from a spectrogram.

        Parameters
        ----------
        spectrogram
            Mel spectrogram.

        top_k
            Number of predictions to return.

        Returns
        -------
        PredictionResult
        """

        if isinstance(

            spectrogram,

            np.ndarray

        ):

            spectrogram = torch.from_numpy(

                spectrogram

            ).float()

        if spectrogram.ndim == 2:

            spectrogram = spectrogram.unsqueeze(0)

        if spectrogram.ndim == 3:

            spectrogram = spectrogram.unsqueeze(0)

        spectrogram = spectrogram.to(self.device)

        start = time.perf_counter()

        with torch.no_grad():

            logits = self.model(

                spectrogram

            )

        inference_time = (

            time.perf_counter()

            - start

        ) * 1000

        return self.postprocessor.process(

            logits,

            top_k=top_k,

            inference_time_ms=inference_time

        )