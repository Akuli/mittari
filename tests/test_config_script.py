from pathlib import Path

from config import (
    list_audio_devices,
    load_config,
    save_config,
    DEFAULT_CONFIG,
    map_percentage_to_gain,
)


def test_listing_audio_devices():
    device_names = list_audio_devices()
    assert len(device_names) >= 10
    assert not any(" " in name for name in device_names)


def test_config_defaults():
    # Should be a copy of DEFAULT_CONFIG
    assert load_config(Path("/dev/null")) == DEFAULT_CONFIG
    assert load_config(Path("/dev/null")) is not DEFAULT_CONFIG


def test_config_file_corner_cases(tmp_path, capsys):
    (tmp_path / "test.conf").write_text('''
asdf = "lol"
left:
    nested = 123
foo:
    abc = "wut"
this line is invalid syntax
''')

    conf = load_config(tmp_path / "test.conf")
    assert conf['asdf'] == 'lol'
    assert conf['left']['nested'] == 123

    output, errors = capsys.readouterr()
    assert not errors
    assert output == (
        "Warning: line 2 of config file contains an unknown key 'asdf'\n"
        + "Warning: line 4 of config file contains an unknown key 'nested'\n"
        + "Warning: line 5 of config file contains an unknown section 'foo'\n"
        + "Warning: line 6 of config file contains an unknown key 'abc'\n"
        + "Warning: line 7 of config file contains invalid syntax\n"
    )

    save_config(conf, tmp_path / "test2.conf")
    output_lines = (tmp_path / "test2.conf").read_text().splitlines()
    assert '    nested = 123' in output_lines
    assert output_lines[-3:] == [
        'asdf = "lol"',
        'foo:',
        '    abc = "wut"',
    ]


def test_example_config(capsys):
    conf = load_config(Path("example-config.conf"))
    assert conf["audio_device"] == "front:CARD=Device,DEV=0"
    assert capsys.readouterr() == ('', '')


def test_map_percentage_to_gain():
    calibration_values = [
        0,      # 0%
        0.02,   # 10%
        0.04,   # 20%
        0.1,    # 30%
        0.2,    # 40%
        0.3,    # 50%
        0.4,    # 60%
        0.5,    # 70%
        0.6,    # 80%
        0.7,    # 90%
        0.8,    # 100%
    ]
    assert map_percentage_to_gain(calibration_values, 0) == 0
    assert map_percentage_to_gain(calibration_values, 100) == 0.8
    assert map_percentage_to_gain(calibration_values, 5) == 0.01
    assert map_percentage_to_gain(calibration_values, 91) == 0.71
