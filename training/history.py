"""
Training History Logger
"""

from pathlib import Path

import pandas as pd


class HistoryLogger:

    def __init__(

        self,

        directory="logs/training"

    ):

        self.records = []

        self.directory = Path(directory)

        self.directory.mkdir(

            parents=True,

            exist_ok=True

        )

        self.history_file = (

            self.directory

            / "history.csv"

        )

    def add(

        self,

        epoch,

        train_loss,

        validation_loss,

        validation_accuracy,

        learning_rate

    ):

        self.records.append({

            "epoch": epoch,

            "train_loss": train_loss,

            "validation_loss": validation_loss,

            "validation_accuracy": validation_accuracy,

            "learning_rate": learning_rate

        })

    def save(self):

        pd.DataFrame(

            self.records

        ).to_csv(

            self.history_file,

            index=False

        )