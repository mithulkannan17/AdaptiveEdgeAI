from models.aura_cnn import AuraCNN
from models.mobilenet_v3 import MobileNetV3Small


class ModelFactory:

    MODELS = {
        "aura_cnn": AuraCNN,
        "auracnn": AuraCNN,      # alias
        "mobilenet_v3_small": MobileNetV3Small,
    }

    @staticmethod
    def build(config):

        name = config["name"].lower()

        if name not in ModelFactory.MODELS:
            raise ValueError(f"Unknown model: {name}")

        model_cls = ModelFactory.MODELS[name]

        common_args = {
            "input_channels": config.get("input_channels", 1),
            "num_classes": config["num_classes"],
            "dropout": config.get("dropout", 0.3),
        }

        if model_cls is MobileNetV3Small:
            return model_cls(
                **common_args,
                pretrained=config.get("pretrained", True),
            )

        return model_cls(**common_args)