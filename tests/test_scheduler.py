import torch.nn as nn

from training.optimizer import OptimizerFactory
from training.scheduler import SchedulerFactory


class DummyModel(nn.Module):

    def __init__(self):

        super().__init__()

        self.fc = nn.Linear(10, 2)

    def forward(self, x):

        return self.fc(x)


def main():

    model = DummyModel()

    optimizer = OptimizerFactory().build(model)

    scheduler = SchedulerFactory().build(optimizer)

    print(type(scheduler).__name__)

    print(scheduler)


if __name__ == "__main__":

    main()