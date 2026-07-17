"""
Metrics Engine for Environmental Sound Classification

Supports:
- Accuracy
- Precision
- Recall
- F1 Score
- Confusion Matrix
- Classification Report
"""

from typing import Dict

import numpy as np
import torch
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)


class Metrics:

    def __init__(self):

        self.reset()

    def reset(self):

        self.predictions = []
        self.targets = []

    def update(self, outputs: torch.Tensor, labels: torch.Tensor):

        preds = torch.argmax(outputs, dim=1)

        self.predictions.extend(
            preds.cpu().numpy().tolist()
        )

        self.targets.extend(
            labels.cpu().numpy().tolist()
        )

    def accuracy(self) -> float:

        predictions = np.array(self.predictions)
        targets = np.array(self.targets)

        return float((predictions == targets).mean())

    def precision(self):

        precision, _, _, _ = precision_recall_fscore_support(
            self.targets,
            self.predictions,
            average="weighted",
            zero_division=0,
        )

        return float(precision)

    def recall(self):

        _, recall, _, _ = precision_recall_fscore_support(
            self.targets,
            self.predictions,
            average="weighted",
            zero_division=0,
        )

        return float(recall)

    def f1_score(self):

        _, _, f1, _ = precision_recall_fscore_support(
            self.targets,
            self.predictions,
            average="weighted",
            zero_division=0,
        )

        return float(f1)

    def confusion_matrix(self):

        return confusion_matrix(
            self.targets,
            self.predictions,
        )

    def classification_report(self, class_names):

        return classification_report(
            self.targets,
            self.predictions,
            target_names=class_names,
            zero_division=0,
        )

    def compute(self) -> Dict:

        return {

            "accuracy": self.accuracy(),

            "precision": self.precision(),

            "recall": self.recall(),

            "f1_score": self.f1_score(),

        }