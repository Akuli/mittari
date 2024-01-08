import json
from pathlib import Path


class Config:
    audio_device: str
    percentage_to_pmw: list[dict[int, float]]

    def __init__(self) -> None:
        self.audio_device = "default"
        self.percentage_to_pmw = [
            {n: n/100 for n in range(0, 101, 10)},  # left channel
            {n: n/100 for n in range(0, 101, 10)},  # right channel
        ]
        self.path = Path.home() / "mittari-config.json"

    def load(self) -> None:
        with self.path.open("r", encoding="utf-8") as file:
            file_content = json.load(file)
        self.audio_device = file_content["audio_device"]
        self.percentage_to_pmw = {
            # Python auto-converts percentages to string.
            # Probably good, because json keys must be strings, like in javascript.
            int(percentage): value
            for percentage, value in file_content["percentage_to_pmw"].items()
        }

    def save(self) -> None:
        file_content = {
            "audio_device": self.audio_device,
            "percentage_to_pmw": self.percentage_to_pmw,
        }

        with self.path.open("w", encoding="utf-8") as file:
            json.dump(file_content, file, indent=4)
            file.write("\n")

    @property
    def num_channels(self) -> int:
        return len(self.percentage_to_pmw)
