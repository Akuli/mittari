import subprocess
import shutil
from shlex import quote
from pathlib import Path
from os import PathLike

import pytest


@pytest.fixture
def mittari():
    subprocess.run(["make", "-s"], check=True)

    def run_the_executable(*args, timeout=None):
        command = ['./mittari', *args]
        if timeout:
            command = ['timeout', str(timeout), *command]

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        assert result.returncode != 0  # should fail
        return result.stdout

    return run_the_executable


def test_cli(mittari):
    assert mittari("--help") == "Usage: ./mittari your-mittari-config-file.conf\n"
    assert mittari("file1.conf", "file2.conf") == "Usage: ./mittari your-mittari-config-file.conf\n"
    assert mittari() == "Usage: ./mittari your-mittari-config-file.conf\n"


def test_special_config_file_errors(mittari, tmp_path):
    assert mittari("nonexistent.conf") == 'mittari error: cannot read config file "nonexistent.conf"\n'
    assert mittari("/dev/null") == 'mittari error: config file "/dev/null" is missing audio_device\n'

    (tmp_path / "foo.conf").write_text('foo = "lol"')
    line1, line2 = mittari(tmp_path / "foo.conf").splitlines()

    assert line1.startswith("mittari warning: config file")
    assert line1.endswith("contains an unknown setting 'foo' on line 1")

    assert line2.startswith("mittari error: config file")
    assert line2.endswith("is missing audio_device")


@pytest.mark.parametrize("bad_config, error", [
    ('    lol = "wut"', "unexpected indentation"),
    ('hello world', "invalid syntax"),
    ('audio_device = "' + 'a' * 1000 + '"', "audio_device is too long"),
    ('left:\n    metric = "FluxCapacitor"', 'metric "FluxCapacitor" not found'),
    ('left:\n    calibration = 0.1 0.2 0.3', "list must start with '['"),
    ('left:\n    calibration = [0.1 0.2 0.3]', "missing ','"),
    ('left:\n    calibration = [0.1, 0.2, 0.3]', "list is too short"),
    ('left:\n    calibration = [' + '0.1,'*10 + '0.2', "list must end with ']'"),
    ('left:\n    calibration = [' + '0.1,'*100, "list is too long"),
])
def test_bad_config_files(mittari, tmp_path, bad_config, error):
    last_line_number = len(bad_config.splitlines())
    (tmp_path / "test.conf").write_text(bad_config)
    assert mittari(tmp_path / "test.conf").endswith(f'", line {last_line_number}: {error}\n')


def test_aplay_invocation(mittari, tmp_path, monkeypatch):
    shutil.copy('tests/fake_aplay.sh', tmp_path / "aplay")
    (tmp_path / "aplay").chmod(0o700)

    monkeypatch.setenv('PATH', str(tmp_path), prepend=":")
    assert mittari("example-config.conf", timeout=0.2) == (
        "message from fake aplay\n"
        + "mittari warning: there seems to be a problem with aplay, restarting in 1 second\n"
    )

    assert (
        (tmp_path / "aplay_args.txt").read_text().strip()
        == '--format S16_LE --rate 44100 --channels 2 --device hw:CARD=Device,DEV=0 --buffer-time 100000'
    )
