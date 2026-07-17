from utils.label_mapper import LabelMapper

mapper = LabelMapper()

tests = [
    "Thunder",
    "Thunderstorm",
    "Rain",
    "Walk_and_footsteps",
    "Bird_vocalization_and_bird_call_and_bird_song",
    "Human_voice",
    "Motor_vehicle_(road)",
    "Animal",
    "Wild_animals",
    "Speech",
]

for t in tests:
    print(f"{t:45} -> {mapper.map_label(t)}")