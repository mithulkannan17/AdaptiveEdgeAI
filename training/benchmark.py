"""
Model Benchmark

Profiles trained models for deployment.
"""

from pathlib import Path
import json
import time

import torch

from managers.config_manager import ConfigManager
from models.model_factory import ModelFactory
from inference.device import DeviceManager


class Benchmark:

    def __init__(self):

        config = ConfigManager()

        self.training_config = config.training()

        self.model_config = config.model()

        self.model_name = self.model_config["name"]

        self.device = DeviceManager.get_device()

        print(f"\nDevice : {self.device}")

        print(f"Benchmarking : {self.model_name}\n")

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

            / "benchmark"

            / self.model_name

        )

        self.output_dir.mkdir(

            parents=True,

            exist_ok=True

        )

    def benchmark(self):

        total_params = sum(

            p.numel()

            for p in self.model.parameters()

        )

        trainable_params = sum(

            p.numel()

            for p in self.model.parameters()

            if p.requires_grad

        )

        model_size_mb = (

            sum(

                p.nelement() * p.element_size()

                for p in self.model.parameters()

            )

            / (1024 ** 2)

        )

        dummy = torch.randn(

            1,

            1,

            128,

            157,

            device=self.device

        )

        # Warm-up

        with torch.no_grad():

            for _ in range(10):

                _ = self.model(dummy)

        if self.device.type == "cuda":

            torch.cuda.synchronize()

        start = time.perf_counter()

        with torch.no_grad():

            for _ in range(100):

                _ = self.model(dummy)

        if self.device.type == "cuda":

            torch.cuda.synchronize()

        elapsed = time.perf_counter() - start

        average_latency = (

            elapsed / 100

        ) * 1000

        throughput = 100 / elapsed

        gpu_memory = 0.0

        if self.device.type == "cuda":

            gpu_memory = (

                torch.cuda.max_memory_allocated()

                / (1024 ** 2)

            )

        results = {

            "model": self.model_name,

            "device": str(self.device),

            "parameters": int(total_params),

            "trainable_parameters": int(trainable_params),

            "model_size_mb": round(model_size_mb, 2),

            "average_latency_ms": round(

                average_latency,

                3

            ),

            "throughput_samples_per_second": round(

                throughput,

                2

            ),

            "gpu_memory_mb": round(

                gpu_memory,

                2

            )

        }

        print("\n")

        print("=" * 60)

        print("Benchmark Results")

        print("=" * 60)

        for key, value in results.items():

            print(f"{key:30}: {value}")

        print("=" * 60)

        with open(

            self.output_dir / "benchmark.json",

            "w"

        ) as file:

            json.dump(

                results,

                file,

                indent=4

            )


if __name__ == "__main__":

    Benchmark().benchmark()