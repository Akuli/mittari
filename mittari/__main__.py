from mittari.config import Config
from mittari.audio_interface import PWMAudioPlayer
from mittari.config_ui import run_gui


def main() -> None:
    config = Config()
    try:
        config.load()
    except FileNotFoundError:
        pass

    player = PWMAudioPlayer(config)
    player.start()

    try:
        run_gui(player)
    finally:
        player.stop_everything()


main()
