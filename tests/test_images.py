import shutil
import subprocess
import glob
import os

import pytest


@pytest.mark.skipif(
    shutil.which("identify") is None,
    reason="imagemagic not installed, it's needed to find image sizes"
)
@pytest.mark.parametrize("image_filename", glob.glob("images/*.jpg"))
def test_jpg_sizes(image_filename):
    output = subprocess.check_output(["identify", image_filename], text=True)
    size = output.split()[2]
    width, height = map(int, size.split("x"))
    assert width <= 1000
    assert height <= 1000


def test_resized_images_exist():
    for filename in os.listdir("images/large-to-be-resized-with-script"):
        assert os.path.exists(f"images/{filename}"), "you need to run images/resize.sh"
