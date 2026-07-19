"""
Callbacks for Training

- Early Stopping
- Model Checkpoint
"""

from pathlib import Path

import torch


class EarlyStopping:

    def __init__(self, patience=10, mode="min"):

        self.patience = patience
        self.mode = mode

        self.counter = 0
        self.best_score = None
        self.stop = False

    def step(self, score):

        if self.best_score is None:

            self.best_score = score

            return False

        improved = (
            score < self.best_score
            if self.mode == "min"
            else score > self.best_score
        )

        if improved:

            self.best_score = score
            self.counter = 0

        else:

            self.counter += 1

            if self.counter >= self.patience:

                self.stop = True

        return self.stop


class ModelCheckpoint:

    def __init__(

        self,

        directory,

        monitor="validation_accuracy",

        mode="max"

    ):

        self.directory = Path(directory)

        self.directory.mkdir(

            parents=True,

            exist_ok=True

        )

        self.monitor = monitor

        self.mode = mode

        self.best_score = None

    def save(

        self,

        model,

        optimizer,

        epoch,

        score,

    ):

        if self.best_score is None:

            improved = True

        else:

            improved = (

                score < self.best_score

                if self.mode == "min"

                else score > self.best_score

            )

        if improved:

            self.best_score = score

            checkpoint = {

                "epoch": epoch,

                "score": score,

                "model_state_dict": model.state_dict(),

                "optimizer_state_dict": optimizer.state_dict(),

            }

            torch.save(

                checkpoint,

                self.directory / "best_model.pth"

            )

            return True

        return False