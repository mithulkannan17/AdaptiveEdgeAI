import torch

from models.aura_cnn import AuraCNN


def count_parameters(model):

    return sum(

        p.numel()

        for p in model.parameters()

        if p.requires_grad

    )


def main():

    model = AuraCNN()

    x = torch.randn(

        8,

        1,

        128,

        157

    )

    y = model(x)

    print("=" * 60)

    print(model)

    print()

    print("=" * 60)

    print("Output Shape")

    print(y.shape)

    print()

    print("=" * 60)

    print("Trainable Parameters")

    print(f"{count_parameters(model):,}")

    print("=" * 60)


if __name__ == "__main__":

    main()