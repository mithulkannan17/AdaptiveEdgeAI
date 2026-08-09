from training.losses import LossFactory


def main():

    criterion = LossFactory().build()

    print(criterion)


if __name__ == "__main__":

    main()