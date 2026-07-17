from pathlib import Path

from utils.logger import setup_logger
from utils.dataset_scanner import DatasetScanner
from utils.dataset_inspector import DatasetInspector
from utils.report_generator import ReportGenerator

from config.settings import DATASETS


def main():

    setup_logger()

    scanner = DatasetScanner()

    inspector = DatasetInspector()

    all_reports = []

    for dataset_name, dataset_path in DATASETS.items():

        print(f"\nScanning {dataset_name}")

        audio_files = scanner.scan(Path(dataset_path))

        report = inspector.inspect(audio_files, dataset_name)

        all_reports.append(report)

    final_report = pd.concat(all_reports, ignore_index=True)

    output_folder = Path("outputs/reports")

    output_folder.mkdir(parents=True, exist_ok=True)

    output_file = output_folder / "dataset_report.csv"

    final_report.to_csv(output_file, index=False)

    ReportGenerator.summarize(final_report)

    print("\nSaved:", output_file)


if __name__ == "__main__":
    import pandas as pd
    main()