"""
Production Trainer for AuraCNN
"""

import torch
from tqdm import tqdm
from torch.amp import autocast, GradScaler

from managers.config_manager import ConfigManager

from models.aura_cnn import AuraCNN

from training.callbacks import (
    EarlyStopping,
    ModelCheckpoint,
)

from training.losses import LossFactory
from training.metrics import Metrics
from training.optimizer import OptimizerFactory
from training.scheduler import SchedulerFactory
from training.datamodule import EnvironmentalDataModule
from training.history import HistoryLogger


class Trainer:

    def __init__(self):

        self.config = ConfigManager().training()

        self.device = self._get_device()

        print(f"\nUsing Device : {self.device}\n")

        self.datamodule = EnvironmentalDataModule(
            batch_size=self.config["batch_size"],
            num_workers=self.config["num_workers"]
        )

        self.datamodule.setup()

        self.model = AuraCNN().to(self.device)

        self.criterion = LossFactory().build().to(self.device)

        self.optimizer = OptimizerFactory().build(self.model)

        self.scheduler = SchedulerFactory().build(
            self.optimizer
        )

        self.metrics = Metrics()

        self.checkpoint = ModelCheckpoint(
            directory=self.config["checkpoint"]["directory"],
            monitor="validation_accuracy",
            mode="max"
        )

        early = self.config["early_stopping"]

        self.early_stopping = EarlyStopping(
            patience=max(20, early["patience"]),
            mode="max"
        )

        self.scaler = GradScaler(
            enabled=self.config["mixed_precision"]
        )

        self.history = HistoryLogger()

    def _get_device(self):

        if torch.cuda.is_available():

            return torch.device("cuda")

        return torch.device("cpu")

    def train(self):

        epochs = self.config["epochs"]

        for epoch in range(1, epochs + 1):

            train_loss = self.train_one_epoch()

            validation_loss, validation_accuracy = self.validate()

            if isinstance(
                self.scheduler,
                torch.optim.lr_scheduler.ReduceLROnPlateau
            ):

                self.scheduler.step(validation_loss)

            else:

                self.scheduler.step()

            saved = self.checkpoint.save(
                self.model,
                self.optimizer,
                epoch,
                validation_accuracy
            )

            lr = self.optimizer.param_groups[0]["lr"]

            self.history.add(
                epoch,
                train_loss,
                validation_loss,
                validation_accuracy,
                lr
            )

            self.history.save()

            print()
            print("=" * 60)
            print(f"Epoch {epoch}/{epochs}")
            print(f"Train Loss       : {train_loss:.4f}")
            print(f"Validation Loss  : {validation_loss:.4f}")
            print(f"Validation Acc   : {validation_accuracy:.4f}")
            print(f"Learning Rate    : {lr:.8f}")

            if saved:

                print("Best model saved.")

            print("=" * 60)

            # Early stopping now follows validation accuracy
            if self.early_stopping.step(validation_accuracy):

                print("\nEarly stopping triggered.")

                break

    def train_one_epoch(self):

        self.model.train()

        running_loss = 0.0

        loader = self.datamodule.train_dataloader()

        progress = tqdm(loader)

        for batch in progress:

            spectrograms = batch["spectrogram"].to(self.device)

            labels = batch["label"].to(self.device)

            self.optimizer.zero_grad(set_to_none=True)

            with autocast(
                device_type=self.device.type,
                enabled=self.config["mixed_precision"]
            ):

                outputs = self.model(spectrograms)

                loss = self.criterion(
                    outputs,
                    labels
                )

            self.scaler.scale(loss).backward()

            self.scaler.unscale_(self.optimizer)

            torch.nn.utils.clip_grad_norm_(
                self.model.parameters(),
                max_norm=1.0
            )

            self.scaler.step(self.optimizer)

            self.scaler.update()

            running_loss += loss.item()

            progress.set_description(
                f"Loss {loss.item():.4f}"
            )

        return running_loss / len(loader)

    def validate(self):

        self.model.eval()

        loader = self.datamodule.validation_dataloader()

        running_loss = 0.0

        self.metrics.reset()

        with torch.no_grad():

            for batch in loader:

                spectrograms = batch["spectrogram"].to(self.device)

                labels = batch["label"].to(self.device)

                with autocast(
                    device_type=self.device.type,
                    enabled=self.config["mixed_precision"]
                ):

                    outputs = self.model(
                        spectrograms
                    )

                    loss = self.criterion(
                        outputs,
                        labels
                    )

                running_loss += loss.item()

                self.metrics.update(
                    outputs,
                    labels
                )

        metric = self.metrics.compute()

        return (
            running_loss / len(loader),
            metric["accuracy"]
        )


if __name__ == "__main__":

    Trainer().train()