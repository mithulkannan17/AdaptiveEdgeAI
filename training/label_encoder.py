"""
Label Encoder
"""

class LabelEncoder:

    CLASSES = [
        "Bird",
        "Wildlife",
        "Human",
        "Vehicle",
        "EmergencyVehicle",
        "Rain",
        "Wind",
        "Chainsaw"
    ]

    def __init__(self):

        self.label_to_id = {
            label: idx
            for idx, label in enumerate(self.CLASSES)
        }

        self.id_to_label = {
            idx: label
            for label, idx in self.label_to_id.items()
        }

    def encode(self, label):

        return self.label_to_id[label]

    def decode(self, idx):

        return self.id_to_label[idx]

    @property
    def num_classes(self):

        return len(self.CLASSES)