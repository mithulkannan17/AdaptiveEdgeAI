"""
Optimizer Factory
"""

import torch.optim as optim

from managers.config_manager import ConfigManager


class OptimizerFactory:

    def __init__(self):

        self.config = ConfigManager().training()

    def build(self, model):

        optimizer_name = self.config["optimizer"]

        learning_rate = self.config["learning_rate"]

        weight_decay = self.config["weight_decay"]

        momentum = self.config.get("momentum", 0.9)

        if optimizer_name == "Adam":

            return optim.Adam(
                model.parameters(),
                lr=learning_rate,
                weight_decay=weight_decay,
            )

        elif optimizer_name == "AdamW":

            return optim.AdamW(
                model.parameters(),
                lr=learning_rate,
                weight_decay=weight_decay,
            )

        elif optimizer_name == "SGD":

            return optim.SGD(
                model.parameters(),
                lr=learning_rate,
                momentum=momentum,
                weight_decay=weight_decay,
            )

        elif optimizer_name == "RMSprop":

            return optim.RMSprop(
                model.parameters(),
                lr=learning_rate,
                momentum=momentum,
                weight_decay=weight_decay,
            )

        else:

            raise ValueError(
                f"Unsupported optimizer: {optimizer_name}"
            )