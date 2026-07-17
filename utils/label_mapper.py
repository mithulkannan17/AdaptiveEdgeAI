"""
label_mapper.py

Maps dataset-specific labels to the project's unified ontology.
"""

from pathlib import Path
from typing import Dict, Optional
import yaml


class LabelMapper:
    """
    Maps original dataset labels into the project's unified labels.

    Example:
        dog -> Wildlife
        crow -> Bird
        speech -> Human
    """

    def __init__(
            self,
            mapping_file: str | Path = "config/label_mapping.yaml"
            ):

        self.mapping_file = Path(mapping_file)

        if not self.mapping_file.exists():
            raise FileNotFoundError(
                f"Mapping file not found: {self.mapping_file}"
            )

        with open(self.mapping_file, "r", encoding="utf-8") as file:
            self.mapping: Dict = yaml.safe_load(file)

        self.reverse_mapping: Dict[str, str] = {}

        self._build_reverse_mapping()

    def _build_reverse_mapping(self) -> None:
        """
        Build reverse lookup dictionary.

        Example:
            dog -> Wildlife
            crow -> Bird
        """

        for unified_label, original_labels in self.mapping.items():

            if not isinstance(original_labels, list):
                continue

            for label in original_labels:

                label = str(label).strip().lower()

                if label in self.reverse_mapping:
                    print(
                        f"Warning: Duplicate label '{label}' "
                        f"found in '{unified_label}'."
                    )

                self.reverse_mapping[label] = unified_label

    def map_label(self, original_label: Optional[str]) -> str:
        """
        Convert an original dataset label into a unified label.
        """

        if original_label is None:
            return "UNMAPPED"

        label = original_label.strip().lower()

        return self.reverse_mapping.get(label, "UNMAPPED")

    def is_mapped(self, original_label: Optional[str]) -> bool:
        """
        Check whether a label exists in the mapping.
        """

        return self.map_label(original_label) != "UNMAPPED"

    def get_mapping(self) -> Dict[str, str]:
        """
        Return reverse mapping dictionary.
        """

        return self.reverse_mapping

    def print_mapping(self) -> None:
        """
        Print all mappings.
        """

        print("\nUnified Label Mapping")
        print("-" * 40)

        for original, unified in sorted(self.reverse_mapping.items()):
            print(f"{original:<25} -> {unified}")