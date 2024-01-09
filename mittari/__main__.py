import sys
import time

from mittari.config import Config
from mittari.system_info import get_cpu_usage, get_mem_usage
from mittari.audio_interface import AudioPlayer, DURATION


def update_meters_forever(player):
    while True:
        player.play([get_cpu_usage() * 100, get_mem_usage() * 100])
        time.sleep(DURATION)


def main() -> None:
    if sys.argv[1:] == ["config"]:
        gui_config_mode = True
    elif sys.argv[1:] == []:
        gui_config_mode = False
    else:
        print("Usage:")
        print(f"  {sys.argv[0]} config      Edit configuration with a GUI")
        print(f"  {sys.argv[0]}             Update meters until interrupted")
        sys.exit(2)

    config = Config()
    try:
        config.load()
    except FileNotFoundError as e:
        print("Loading config file failed:", e)
        pass

    player = AudioPlayer(config)
    player.start()

    try:
        if gui_config_mode:
            # Import here, in case tkinter doesn't work.
            # You can still run it if config manually json file in text editor.
            from mittari.config_gui import run_gui
            run_gui(player)
        else:
            update_meters_forever(player)
    finally:
        player.stop_everything()


main()
