from preprocessing.batch_standardizer import BatchStandardizer


def main():

    processor = BatchStandardizer()

    processor.process_dataset()


if __name__ == "__main__":

    main()