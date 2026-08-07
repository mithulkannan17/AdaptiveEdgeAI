"""
Model Evaluator
"""

from pathlib import Path
import json

import matplotlib.pyplot as plt
import pandas as pd
import torch
from torch.amp import autocast

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    ConfusionMatrixDisplay,
)

from managers.config_manager import ConfigManager
from models.model_factory import ModelFactory
from training.datamodule import EnvironmentalDataModule
from training.label_encoder import LabelEncoder
from inference.device import DeviceManager


class Evaluator:

    def __init__(self):

        config = ConfigManager()

        self.training_config = config.training()

        self.model_config = config.model()

        self.model_name = self.model_config["name"]

        self.device = DeviceManager.get_device()

        print(f"\nUsing Device : {self.device}")

        print(f"Evaluating   : {self.model_name}\n")

        self.encoder = LabelEncoder()

        self.datamodule = EnvironmentalDataModule(

            batch_size=self.training_config["batch_size"],

            num_workers=self.training_config["num_workers"]

        )

        self.datamodule.setup()

        self.model = (

            ModelFactory

            .build(self.model_config)

            .to(self.device)

        )

        checkpoint_path = (

            Path(

                self.training_config["checkpoint"]["directory"]

            )

            / self.model_name

            / "best_model.pth"

        )

        if not checkpoint_path.exists():

            raise FileNotFoundError(

                f"Checkpoint not found:\n{checkpoint_path}"

            )

        checkpoint = torch.load(

            checkpoint_path,

            map_location=self.device

        )

        self.model.load_state_dict(

            checkpoint["model_state_dict"]

        )

        self.model.eval()

        self.output_dir = (

            Path("logs")

            / "evaluation"

            / self.model_name

        )

        self.output_dir.mkdir(

            parents=True,

            exist_ok=True

        )

    def evaluate(self):

        loader = self.datamodule.test_dataloader()

        predictions = []

        targets = []

        rows = []

        with torch.no_grad():

            for batch in loader:

                spectrograms = batch["spectrogram"].to(self.device)

                labels = batch["label"].to(self.device)

                with autocast(

                    device_type=self.device.type,

                    enabled=self.training_config["mixed_precision"]

                ):

                    outputs = self.model(

                        spectrograms

                    )

                preds = outputs.argmax(dim=1)

                predictions.extend(

                    preds.cpu().tolist()

                )

                targets.extend(

                    labels.cpu().tolist()

                )

                for i in range(len(preds)):

                    rows.append({

                        "filepath": batch["filepath"][i],

                        "true_label":

                            self.encoder.decode(

                                int(labels[i])

                            ),

                        "predicted_label":

                            self.encoder.decode(

                                int(preds[i])

                            )

                    })

        self.save_metrics(

            targets,

            predictions

        )

        self.save_predictions(

            rows

        )

        print("\nEvaluation Complete.")

        print(f"Results saved to:\n{self.output_dir}")

    def save_metrics(

        self,

        y_true,

        y_pred

    ):

        accuracy = accuracy_score(

            y_true,

            y_pred

        )

        report = classification_report(

            y_true,

            y_pred,

            target_names=self.encoder.classes,

            output_dict=True,

            zero_division=0

        )

        cm = confusion_matrix(

            y_true,

            y_pred

        )

        metrics = {

            "model": self.model_name,

            "accuracy": float(accuracy)

        }

        with open(

            self.output_dir / "metrics.json",

            "w"

        ) as file:

            json.dump(

                metrics,

                file,

                indent=4

            )

        pd.DataFrame(

            report

        ).transpose().to_csv(

            self.output_dir / "classification_report.csv"

        )

        disp = ConfusionMatrixDisplay(

            confusion_matrix=cm,

            display_labels=self.encoder.classes

        )

        fig, ax = plt.subplots(

            figsize=(12, 12)

        )

        disp.plot(

            ax=ax,

            xticks_rotation=90,

            colorbar=False

        )

        plt.tight_layout()

        plt.savefig(

            self.output_dir / "confusion_matrix.png",

            dpi=300

        )

        plt.close(fig)

    def save_predictions(

        self,

        rows

    ):

        pd.DataFrame(

            rows

        ).to_csv(

            self.output_dir / "predictions.csv",

            index=False

        )


if __name__ == "__main__":

    Evaluator().evaluate()