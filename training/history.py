"""
Training History Logger
"""

from pathlib import Path

import pandas as pd


class HistoryLogger:

    def __init__(self):

        self.records = []

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

    def save(

        self,

        path="logs/training/history.csv"

    ):

        path = Path(path)

        path.parent.mkdir(

            parents=True,

            exist_ok=True

        )

        pd.DataFrame(

            self.records

        ).to_csv(

            path,

            index=False

        )