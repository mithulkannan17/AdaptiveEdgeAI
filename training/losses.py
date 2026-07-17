"""
Loss Function Factory
"""

import torch
import torch.nn as nn

from managers.config_manager import ConfigManager


class LossFactory:

    def __init__(self):

        self.config = ConfigManager().training()

    def build(self):

        loss_name = self.config["training"]["loss"]

        if loss_name == "CrossEntropy":

            return nn.CrossEntropyLoss()

        elif loss_name == "NLLLoss":

            return nn.NLLLoss()

        elif loss_name == "MSELoss":

            return nn.MSELoss()

        else:

            raise ValueError(
                f"Unsupported loss function: {loss_name}"
            )