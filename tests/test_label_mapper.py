from utils.label_mapper import LabelMapper

mapper = LabelMapper("config/label_mapping.yaml")

labels = [

    "dog",

    "crow",

    "speech",

    "chainsaw",

    "ambulance_siren",

    "rain",

    "wind",

    "alien"

]

for label in labels:

    print(

        f"{label:20} -> {mapper.map_label(label)}"

    )