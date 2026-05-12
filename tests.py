import glob
import os
import tempfile
import contextlib
import io
import sys
import subprocess
import shutil
import traceback
from pathlib import Path

from config import (
    list_audio_devices,
    load_config,
    save_config,
    DEFAULT_CONFIG,
    map_percentage_to_gain,
)


def test_listing_audio_devices():
    if shutil.which("aplay") is None:
        return "skipped because aplay is not installed"

    device_names = list_audio_devices()  # uses 'aplay -L'
    assert len(device_names) >= 10
    assert not any(" " in name for name in device_names)


def test_config_defaults():
    # Should be a copy of DEFAULT_CONFIG
    assert load_config(Path("/dev/null")) == DEFAULT_CONFIG
    assert load_config(Path("/dev/null")) is not DEFAULT_CONFIG


def test_config_file_corner_cases():
    with tempfile.TemporaryDirectory() as tempdir:
        (Path(tempdir) / "test.conf").write_text("""
asdf = "lol"
left:
    nested = 123
foo:
    abc = "wut"
this line is invalid syntax
""")

        with contextlib.redirect_stdout(io.StringIO()) as output:
            conf = load_config(Path(tempdir) / "test.conf")

        assert conf["asdf"] == "lol"
        assert conf["left"]["nested"] == 123
        assert output.getvalue() == (
            "Warning: line 2 of config file contains an unknown key 'asdf'\n"
            + "Warning: line 4 of config file contains an unknown key 'nested'\n"
            + "Warning: line 5 of config file contains an unknown section 'foo'\n"
            + "Warning: line 6 of config file contains an unknown key 'abc'\n"
            + "Warning: line 7 of config file contains invalid syntax\n"
        )

        save_config(conf, Path(tempdir) / "test2.conf")
        output_lines = (Path(tempdir) / "test2.conf").read_text().splitlines()
        assert "    nested = 123" in output_lines
        assert output_lines[-3:] == [
            'asdf = "lol"',
            "foo:",
            '    abc = "wut"',
        ]


def test_example_config():
    conf = load_config(Path("example-config.conf"))
    assert conf["audio_device"] == "hw:CARD=Device,DEV=0"


def test_map_percentage_to_gain():
    calibration_values = [
        0,  # 0%
        0.02,  # 10%
        0.04,  # 20%
        0.1,  # 30%
        0.2,  # 40%
        0.3,  # 50%
        0.4,  # 60%
        0.5,  # 70%
        0.6,  # 80%
        0.7,  # 90%
        0.8,  # 100%
    ]
    assert map_percentage_to_gain(calibration_values, 0) == 0
    assert map_percentage_to_gain(calibration_values, 100) == 0.8
    assert map_percentage_to_gain(calibration_values, 5) == 0.01
    assert map_percentage_to_gain(calibration_values, 91) == 0.71


def mittari(*args, timeout=None):
    subprocess.run(["make", "-s"], check=True)

    command = ["./mittari", *args]
    if timeout:
        command = ["timeout", str(timeout), *command]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    assert result.returncode != 0  # should fail
    return result.stdout


def test_cli():
    assert mittari("--help") == "Usage: ./mittari your-mittari-config-file.conf\n"
    assert (
        mittari("file1.conf", "file2.conf")
        == "Usage: ./mittari your-mittari-config-file.conf\n"
    )
    assert mittari() == "Usage: ./mittari your-mittari-config-file.conf\n"


def test_special_config_file_errors():
    assert (
        mittari("nonexistent.conf")
        == 'mittari error: cannot read config file "nonexistent.conf"\n'
    )
    assert (
        mittari("/dev/null")
        == 'mittari error: config file "/dev/null" is missing audio_device\n'
    )

    with tempfile.TemporaryDirectory() as tempdir:
        (Path(tempdir) / "foo.conf").write_text('foo = "lol"')
        line1, line2 = mittari(Path(tempdir) / "foo.conf").splitlines()

    assert line1.startswith("mittari warning: config file")
    assert line1.endswith("contains an unknown setting 'foo' on line 1")

    assert line2.startswith("mittari error: config file")
    assert line2.endswith("is missing audio_device")


def test_bad_config_files():
    cases = [
        ('    lol = "wut"', "unexpected indentation"),
        ("hello world", "invalid syntax"),
        ('audio_device = "' + "a" * 1000 + '"', "audio_device is too long"),
        ('left:\n    metric = "FluxCapacitor"', 'metric "FluxCapacitor" not found'),
        ("left:\n    calibration = 0.1 0.2 0.3", "list must start with '['"),
        ("left:\n    calibration = [0.1 0.2 0.3]", "missing ','"),
        ("left:\n    calibration = [0.1, 0.2, 0.3]", "list is too short"),
        ("left:\n    calibration = [" + "0.1," * 10 + "0.2", "list must end with ']'"),
        ("left:\n    calibration = [" + "0.1," * 100, "list is too long"),
    ]

    for bad_config, error in cases:
        last_line_number = len(bad_config.splitlines())
        with tempfile.TemporaryDirectory() as tempdir:
            (Path(tempdir) / "test.conf").write_text(bad_config)
            assert mittari(Path(tempdir) / "test.conf").endswith(
                f'", line {last_line_number}: {error}\n'
            )


def test_aplay_invocation():
    with tempfile.TemporaryDirectory() as tempdir:
        # Create a fake aplay script that prints a message and stores the
        # command-line arguments, so we can see how it was called.
        (Path(tempdir) / "aplay").write_text(r"""
#!/bin/bash
echo "message from fake aplay" >&2
echo "$@" > "$(dirname "$0")"/aplay_args.txt
""".lstrip())
        (Path(tempdir) / "aplay").chmod(0o700)

        old_path = os.environ["PATH"]
        try:
            # Adjust PATH so that mittari finds the fake aplay, not the real one
            os.environ["PATH"] = tempdir + ":" + os.environ["PATH"]

            assert mittari("example-config.conf", timeout=0.2) == (
                "message from fake aplay\n"
                + "mittari warning: there seems to be a problem with aplay, restarting in 1 second\n"
            )

        finally:
            os.environ["PATH"] = old_path

        assert (
            Path(tempdir) / "aplay_args.txt"
        ).read_text().strip() == "--format S16_LE --rate 44100 --channels 2 --device hw:CARD=Device,DEV=0 --buffer-time 100000"


def test_jpg_sizes():
    if shutil.which("identify") is None:
        return "skipping because imagemagic is not installed"

    for image_filename in glob.glob("images/*.jpg"):
        output = subprocess.check_output(["identify", image_filename], text=True)
        size = output.split()[2]
        width, height = map(int, size.split("x"))
        assert width <= 1000
        assert height <= 1000


def test_resized_images_exist():
    for filename in os.listdir("images/large-to-be-resized-with-script"):
        assert os.path.exists(f"images/{filename}"), "you need to run images/resize.sh"


GREEN = "\x1b[32m"
RED = "\x1b[31m"
RESET = "\x1b[0m"


def main():
    errors = []

    for func_name, func in globals().items():
        if func_name.startswith("test_") and callable(func):
            print(func_name.ljust(40), end=" ", flush=True)
            try:
                print(func() or (GREEN + "ok" + RESET))
            except Exception as e:
                error_name = type(e).__name__
                error_message = "".join(traceback.format_exc().rstrip("\n"))
                print(RED + error_name + RESET)
                errors.append((func_name, error_name, error_message))

    for func_name, error_name, error_message in errors:
        print()
        print(RED + f" {error_name} in {func_name} ".center(70, "=") + RESET)
        print(error_message)

    sys.exit(1 if errors else 0)


main()
