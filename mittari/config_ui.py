import tkinter
from functools import partial
from typing import cast, Any
from tkinter import ttk, messagebox

from mittari.config import Config
from mittari.audio_interface import PMWAudioPlayer, list_audio_devices


def on_slider_moved(player: PMWAudioPlayer, channel_num: int, percentage: int, new_value: str) -> None:
    player.config.percentage_to_pwm[channel_num][percentage] = float(new_value) / 100
    player.play_single_channel(channel_num, percentage)


def create_meter_configurator(
    player: PMWAudioPlayer,
    parent: ttk.Frame,
    text: str,
    channel_num: int,
) -> ttk.LabelFrame:
    container = ttk.LabelFrame(parent, text=text)
    container.grid_columnconfigure(1, weight=1)

    for y, percentage in enumerate(range(0, 101, 10)):
        pwm_value = player.config.percentage_to_pwm[channel_num][percentage]
        label = ttk.Label(container, text=f"{percentage}%:")
        slider = ttk.Scale(
            container,
            from_=0,
            to=100,
            value=100 * pwm_value,
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


def run_gui(player: PMWAudioPlayer) -> None:
    root = tkinter.Tk()
    root.title("Mittari Configurator")
    root.minsize(700, 500)

    big_frame = ttk.Frame(root)
    big_frame.pack(fill="both", expand=True)

    device_selector = create_device_selector(big_frame, player.config)
    device_selector.grid(row=0, column=0, columnspan=2, padx=10, pady=20)

    left = create_meter_configurator(
        player, big_frame, "Calibration for CPU Usage (left)", 0
    )
    right = create_meter_configurator(
        player, big_frame, "Calibration for Memory (right)", 1
    )

    left.grid(row=1, column=0, sticky="nswe", padx=5, pady=10)
    right.grid(row=1, column=1, sticky="nswe", padx=5, pady=10)

    big_frame.grid_rowconfigure(1, weight=1)
    big_frame.grid_columnconfigure([0, 1], weight=1)

    ttk.Separator(root).pack(fill="x")

    button_frame = ttk.Frame(root)
    button_frame.pack(fill="x")

    ok_button = ttk.Button(button_frame, text="Save and Exit", command=(lambda: save_and_exit(root, player.config)))
    cancel_button = ttk.Button(button_frame, text="Cancel", command=root.destroy)

    ok_button.pack(side="right")
    cancel_button.pack(side="right")

    status_bar = ttk.Label(root)
    status_bar.pack(fill="x")

    root.protocol("WM_DELETE_WINDOW", (lambda: confirm_and_quit(root, player.config)))
    root.mainloop()
