from mittari.audio_interface import list_audio_devices


def test_listing_audio_devices():
    device_names = list_audio_devices()
    assert "default" in device_names
    assert not any(" " in name for name in device_names)
