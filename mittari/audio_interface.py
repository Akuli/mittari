import subprocess
import sys
import threading
import time

from mittari.config import Config


def list_audio_devices() -> list[str]:
    output = subprocess.check_output(["aplay", "-L"], text=True)
    return [
        line.strip()
        for line in output.splitlines()
        if ":" in line and not line.startswith(" ")
    ]


def map_percentage_to_pwm(config: Config, channel_num: int, percentage: float) -> float:
    assert 0 <= percentage <= 100
    percentage_to_pwm = config.percentage_to_pwm[channel_num]

    # Pick surrounding two values and do linear interpolation
    zero_to_100 = sorted(percentage_to_pwm.keys())
    assert 0 in zero_to_100
    assert 100 in zero_to_100

    for lower, upper in zip(zero_to_100[:-1], zero_to_100[1:]):
        if lower <= percentage <= upper:
            lower_pwm = percentage_to_pwm[lower]
            upper_pwm = percentage_to_pwm[upper]
            slope = (upper_pwm - lower_pwm)/(upper - lower)
            return lower_pwm + slope*(percentage - lower)

    raise RuntimeError("this should not be possible...")


SAMPLE_RATE = 44100
FREQUENCY = 1000


def construct_audio_data(config: Config, values: list[float | None]) -> bytes:
    pwm_values = []
    for channel_num, percentage in enumerate(values):
        if percentage is None:
            pwm_values.append(0.0)
        else:
            pwm_values.append(map_percentage_to_pwm(config, channel_num, percentage))

    duration = 0.1
    audio_data = bytearray()

    for sample_num in range(round(duration * SAMPLE_RATE)):
        for pwm in pwm_values:
            time = sample_num / SAMPLE_RATE
            phase = (time * FREQUENCY) % 1
            if phase < pwm:
                sample = 0x7fff
            else:
                sample = 0
            audio_data += sample.to_bytes(2, byteorder="little", signed=True)

    return bytes(audio_data)


class PMWAudioPlayer:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.thread: threading.Thread | None = None
        self._now_playing: list[float | None] = []
        self.stopping: bool = False

    def get_command(self) -> list[str]:
        return [
            "aplay",
            "--format",
            "S16_LE",
            "--rate",
            str(SAMPLE_RATE),
            "--channels",
            str(len(self.config.percentage_to_pwm)),
            "--device",
            self.config.audio_device,
            "--buffer-size",
            "1000",
        ]

    def start(self) -> None:
        if self.thread is not None:
            return  # already started

        self.stopping = False
        self.thread = threading.Thread(target=self._feed_audio_to_process)
        self.thread.start()

    def stop_everything(self) -> None:
        self.stopping = True
        if self.thread is not None:
            self.thread.join()

    def play(self, percentages: list[float | None]) -> None:
        print("Play percentages:", percentages)
        self._now_playing = percentages

    def play_single_channel(self, channel_num: int, percentage: float) -> None:
        percentages: list[float | None] = [None] * self.config.num_channels
        percentages[channel_num] = percentage
        self.play(percentages)

    def stop_playing(self) -> None:
        self.play([None] * self.config.num_channels)

    def _feed_audio_to_process(self) -> None:
        process = None
        command = None

        try:
            while not self.stopping:
                if process is None or command != self.get_command():
                    # Params changed --> start new aplay subprocess
                    if process is not None:
                        process.kill()

                    command = self.get_command()
                    process = subprocess.Popen(command, stdin=subprocess.PIPE, pipesize=1000)

                assert process is not None
                assert process.stdin is not None

                audio_data = construct_audio_data(self.config, self._now_playing)
                try:
                    process.stdin.write(audio_data)
                    process.stdin.flush()
                except OSError as e:
                    print("error running subprocess:", e, file=sys.stderr)
                    print("trying again after 1 second", file=sys.stderr)
                    process.kill()
                    process = None
                    time.sleep(1)

        finally:
            if process is not None:
                process.kill()
            self.now_running_command = None
