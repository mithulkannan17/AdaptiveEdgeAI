import torch

from training.metrics import Metrics


def main():

    metrics = Metrics()

    outputs = torch.tensor([
        [0.8, 0.2],
        [0.3, 0.7],
        [0.6, 0.4],
        [0.1, 0.9],
    ])

    labels = torch.tensor([
        0,
        1,
        1,
        1,
    ])

    metrics.update(outputs, labels)

    print(metrics.compute())

    print()

    print(metrics.confusion_matrix())


if __name__ == "__main__":
    main()