from mittari.config import Config


def test_has_changed(tmp_path):
    config = Config(path=tmp_path / "mittari-config.json")
    assert not config.has_changed()

    config.audio_device = "foo:bar"
    assert config.has_changed()
    config.save()
    assert not config.has_changed()

    config.percentage_to_gain[0][60] = 0.0789
    assert config.has_changed()
    config.save()
    assert not config.has_changed()


def test_load_and_save(tmp_path):
    config = Config(path=tmp_path / "mittari-config.json")
    config.percentage_to_gain[0][60] = 0.0789
    config.save()

    config2 = Config(path=tmp_path / "mittari-config.json")
    assert config2.percentage_to_gain[0][60] == 0.06  # default
    config2.load()
    assert config2.percentage_to_gain[0][60] == 0.0789
