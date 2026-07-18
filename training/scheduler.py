"""
Learning Rate Scheduler Factory
"""

import torch.optim.lr_scheduler as lr_scheduler

from managers.config_manager import ConfigManager


class SchedulerFactory:

    def __init__(self):

        self.config = ConfigManager().training()["training"]

    def build(self, optimizer):

        scheduler_name = self.config["scheduler"]

        epochs = self.config["epochs"]

        if scheduler_name == "CosineAnnealingLR":

            return lr_scheduler.CosineAnnealingLR(

                optimizer,

                T_max=epochs,

                eta_min=self.config["eta_min"]

            )

        elif scheduler_name == "StepLR":

            return lr_scheduler.StepLR(

                optimizer,

                step_size=self.config["step_size"],

                gamma=self.config["gamma"]

            )

        elif scheduler_name == "ExponentialLR":

            return lr_scheduler.ExponentialLR(

                optimizer,

                gamma=self.config["gamma"]

            )

        elif scheduler_name == "ReduceLROnPlateau":

            return lr_scheduler.ReduceLROnPlateau(

                optimizer,

                mode="min",

                factor=self.config["gamma"],

                patience=5

            )

        else:

            raise ValueError(

                f"Unsupported scheduler: {scheduler_name}"

            )