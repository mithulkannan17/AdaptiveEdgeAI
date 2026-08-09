from managers.config_manager import ConfigManager


def main():

    config = ConfigManager()

    training = config.training()

    print("=" * 50)
    print("Training Configuration")
    print("=" * 50)

    print(training)


if __name__ == "__main__":
    main()