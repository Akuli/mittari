import copy
import json
from pathlib import Path
from typing import Any


# The hardware has room for systems that output a quiet signal from headphones
# jack. Exposing it unnecessarily makes the sliders annoyingly sensitive,
# because only a short section in the beginning of the slider is usable.
MAX_GAIN = 0.02


class Config:
    audio_device: str
    percentage_to_gain: list[dict[int, float]]

    def __init__(self, *, path: Path | None = None) -> None:
        self.audio_device = "default"
        self.percentage_to_gain = [
            {n: n/100*MAX_GAIN for n in range(0, 101, 10)},  # left channel
            {n: n/100*MAX_GAIN for n in range(0, 101, 10)},  # right channel
        ]
        if path is None:
            self.path = Path.home() / "mittari-config.json"
        else:
            self.path = path
        self._last_saved = self.get_file_content_to_save()

    def get_file_content_to_save(self) -> dict[str, Any]:
        return copy.deepcopy({
            "audio_device": self.audio_device,
            "percentage_to_gain": self.percentage_to_gain,
        })

    def has_changed(self) -> bool:
        return self._last_saved != self.get_file_content_to_save()

    def load(self) -> None:
        with self.path.open("r", encoding="utf-8") as file:
            file_content = json.load(file)
        self.audio_device = file_content["audio_device"]
        self.percentage_to_gain = [
            {
                # Python auto-converts percentages to string.
                # Probably good, because json keys must be strings, like in javascript.
                int(percentage): value
                for percentage, value in channel_mapping.items()
            }
            for channel_mapping in file_content["percentage_to_gain"]
        ]

        self._last_saved = self.get_file_content_to_save()
        print("Loaded config from", self.path)

    def save(self) -> None:
        content = self.get_file_content_to_save()
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(content, file, indent=4)
            file.write("\n")

        self._last_saved = content
        print("Saved config to", self.path)

    @property
    def num_channels(self) -> int:
        return len(self.percentage_to_gain)
