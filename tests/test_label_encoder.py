from training.label_encoder import LabelEncoder


def main():

    encoder = LabelEncoder()

    encoder.print_summary()

    print()

    print(encoder.encode("Bird"))

    print(encoder.encode("Speech"))

    print(encoder.decode(0))


if __name__ == "__main__":
    main()