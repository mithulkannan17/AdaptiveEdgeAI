"""
Integration test for Predictor + Unknown Discovery.

Uses a temporary checkpoint generated from the same model
architecture used by the production ModelLoader.

The test does not depend on the production trained checkpoint.
"""

import torch

from managers.config_manager import ConfigManager
from models.model_factory import ModelFactory
from inference.predictor import Predictor


def test_predictor_unknown_discovery(
    tmp_path,
    monkeypatch,
):
    """
    Verify that Predictor can:

    1. Load a checkpoint.
    2. Perform inference.
    3. Run unknown-sound detection.
    4. Return a discovery result.
    """

    # ======================================================
    # Test Model Configuration
    # ======================================================

    original_model_config = (
        ConfigManager.model
    )

    def test_model_config(self):

        config = dict(
            original_model_config(self)
        )

        # Do not download ImageNet weights during tests.
        config["pretrained"] = False

        return config

    monkeypatch.setattr(
        ConfigManager,
        "model",
        test_model_config,
    )

    # ======================================================
    # Build the SAME architecture used by ModelLoader
    # ======================================================

    config = ConfigManager().model()

    model = (
        ModelFactory
        .build(config)
    )

    model.eval()

    # ======================================================
    # Temporary Checkpoint
    # ======================================================

    checkpoint_path = (
        tmp_path
        / "best_model.pth"
    )

    torch.save(
        {
            "model_state_dict":
                model.state_dict(),

        },
        checkpoint_path,
    )

    # ======================================================
    # Predictor
    # ======================================================

    predictor = Predictor(

        checkpoint_path=checkpoint_path,

        enable_unknown_discovery=True,

        unknown_confidence_threshold=0.99,

        unknown_margin_threshold=0.90,

    )

    # ======================================================
    # Test Spectrogram
    # ======================================================

    spectrogram = torch.randn(

        1,
        1,
        128,
        157,

    )

    # ======================================================
    # Prediction
    # ======================================================

    result = (
        predictor.predict_spectrogram(
            spectrogram
        )
    )

    assert result is not None

    # ======================================================
    # Unknown Discovery
    # ======================================================

    discovery = (
        predictor.get_last_discovery_result()
    )

    assert discovery is not None

    assert (
        discovery.decision
        is not None
    )