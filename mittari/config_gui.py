import random
import tkinter
from functools import partial
from typing import cast, Any
from tkinter import ttk, messagebox

from mittari.config import Config, MAX_GAIN
from mittari.audio_interface import AudioPlayer, list_audio_devices


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


def on_slider_moved(player: AudioPlayer, channel_num: int, percentage: int, new_value: str) -> None:
    player.config.percentage_to_gain[channel_num][percentage] = float(new_value) / 100 * MAX_GAIN
    player.play_single_channel(channel_num, percentage)


def create_meter_configurator(
    player: AudioPlayer,
    parent: ttk.Frame,
    text: str,
    channel_num: int,
) -> ttk.LabelFrame:
    container = ttk.LabelFrame(parent, text=text)
    container.grid_columnconfigure(1, weight=1)

    for y, percentage in enumerate(range(0, 101, 10)):
        gain = player.config.percentage_to_gain[channel_num][percentage]
        label = ttk.Label(container, text=f"{percentage}%:")
        slider = ttk.Scale(
            container,
            from_=0,
            to=100,
            value=100 * gain / MAX_GAIN,
            command=partial(on_slider_moved, player, channel_num, percentage),
        )

        slider.bind(
            "<Enter>",
            (lambda event, p=percentage: player.play_single_channel(channel_num, p)),  # type: ignore
        )
        slider.bind("<Leave>", (lambda event: player.stop_playing()))

        label.grid(row=y, column=0)
        slider.grid(row=y, column=1, sticky="we")

    return container


def create_test_button(player: AudioPlayer, parent: ttk.Frame) -> ttk.Button:
    def start_test() -> None:
        left = random.randint(0, 100)
        right = random.randint(0, 100)
        player.play([left, right])

    button = ttk.Button(parent, text="Test the configuration", command=start_test)
    button.pack(padx=5, pady=5)
    button.bind("<Leave>", (lambda e: player.stop_playing()))

    return button


def create_status_label(player: AudioPlayer, parent: ttk.Frame) -> ttk.Label:
    label = ttk.Label(parent)

    def update() -> None:
        label.after(50, update)

        left, right = player.now_playing or [None, None]
        if left is not None and right is not None:
            text = f"Left meter should be at {left}% and right at {right}%."
        elif left is not None:
            text = f"Left meter should be at {left}%."
        elif right is not None:
            text = f"Right meter should be at {right}%."
        else:
            text = ""
        label.config(text=text)

    update()
    return label


def save_and_exit(root: tkinter.Tk, config: Config) -> None:
    config.save()
    root.destroy()


def confirm_and_quit(root: tkinter.Tk, config: Config) -> None:
    if config.has_changed():
        result = messagebox.askyesnocancel("Mittari Configurator", "Do you want to save your changes?")
        if result is None:
            # cancel pressed
            return
        if result:
            config.save()
    root.destroy()


def run_gui(player: AudioPlayer) -> None:
    root = tkinter.Tk()
    root.title("Mittari Configurator")
    root.minsize(700, 500)

    big_frame = ttk.Frame(root)
    big_frame.pack(fill="both", expand=True)

    device_selector = create_device_selector(big_frame, player.config)
    device_selector.pack(padx=10, pady=20)

    meter_configurator_container = ttk.Frame(big_frame)
    meter_configurator_container.pack(fill="both", expand=True)

    left = create_meter_configurator(
        player, meter_configurator_container, "Calibration for CPU Usage (left)", 0
    )
    right = create_meter_configurator(
        player, meter_configurator_container, "Calibration for Memory (right)", 1
    )

    left.pack(side="left", fill="both", expand=True, padx=5, pady=10)
    right.pack(side="right", fill="both", expand=True, padx=5, pady=10)

    create_test_button(player, big_frame).pack()
    create_status_label(player, big_frame).pack()

    ttk.Separator(root).pack(fill="x")

    button_frame = ttk.Frame(root)
    button_frame.pack(fill="x")

    ok_button = ttk.Button(button_frame, text="Save and Exit", command=(lambda: save_and_exit(root, player.config)))
    cancel_button = ttk.Button(button_frame, text="Cancel", command=root.destroy)

    ok_button.pack(side="right", padx=5, pady=5)
    cancel_button.pack(side="right", padx=5, pady=5)

    root.protocol("WM_DELETE_WINDOW", (lambda: confirm_and_quit(root, player.config)))
    root.mainloop()
