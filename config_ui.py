import tkinter
from functools import partial
from typing import cast, Any
from tkinter import ttk

from config import Config
from audio_interface import PMWAudioPlayer, list_audio_devices


def play_single_channel(
    player: PMWAudioPlayer,
    channel_num: int,
    percentage: int,
    *junk: object,
) -> None:
    player.now_playing = [None] * player.config.num_channels
    player.now_playing[channel_num] = percentage


def on_slider_moved(player: PMWAudioPlayer, channel_num: int, percentage: int, new_value: str) -> None:
    player.config.percentage_to_pmw[channel_num][percentage] = float(new_value) / 100
    play_single_channel(player, channel_num, percentage)


def create_meter_configurator(
    player: PMWAudioPlayer,
    config: Config,
    parent: ttk.Frame,
    text: str,
    channel_num: int,
) -> ttk.LabelFrame:
    container = ttk.LabelFrame(parent, text=text)
    container.grid_columnconfigure(1, weight=1)

    for y, percentage in enumerate(range(0, 101, 10)):
        label = ttk.Label(container, text=f"{percentage}%:")
        slider = ttk.Scale(
            container,
            from_=0,
            to=100,
            command=partial(on_slider_moved, player, channel_num, percentage),
        )

        label.grid(row=y, column=0)
        slider.grid(row=y, column=1, sticky="we")

    return container


def create_device_selector(parent: ttk.Frame, config: Config) -> ttk.Frame:
    container = ttk.Frame(parent)
    ttk.Label(container, text="Audio Device: ").pack(side="left")

    var = tkinter.StringVar()
    var.set(config.audio_device)
    var.trace_add("write", lambda *junk: setattr(config, "audio_device", var.get()))
    selector = ttk.Combobox(container, textvariable=var, values=list_audio_devices(), width=30)
    selector.pack(side="left")

    cast(Any, selector).i_dont_want_garbage_collection_to_eat_the_var = var
    return container


def main() -> None:
    root = tkinter.Tk()
    root.title("Mittari Configurator")
    root.minsize(700, 500)

    config = Config()
    player = PMWAudioPlayer(config)
    player.start()

    big_frame = ttk.Frame(root)
    big_frame.pack(fill="both", expand=True)

    device_selector = create_device_selector(big_frame, config)
    device_selector.grid(row=0, column=0, columnspan=2, padx=10, pady=20)

    left = create_meter_configurator(
        player, config, big_frame, "Calibration for CPU Usage (left)", 0
    )
    right = create_meter_configurator(
        player, config, big_frame, "Calibration for Memory (right)", 1
    )

    left.grid(row=1, column=0, sticky="nswe", padx=5, pady=10)
    right.grid(row=1, column=1, sticky="nswe", padx=5, pady=10)

    big_frame.grid_rowconfigure(1, weight=1)
    big_frame.grid_columnconfigure([0, 1], weight=1)

    ttk.Separator(root).pack(fill="x")

    button_frame = ttk.Frame(root)
    button_frame.pack(fill="x")

    ttk.Button(button_frame, text="Save").pack(side="right")
    ttk.Button(button_frame, text="Cancel", command=root.destroy).pack(side="right")

    root.mainloop()


main()
