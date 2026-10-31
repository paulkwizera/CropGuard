import tempfile
from pathlib import Path

from django.test import SimpleTestCase
from PIL import Image

from .services import imaging


class ShrinkTests(SimpleTestCase):
    def make(self, name, size, orientation=1, fmt="JPEG"):
        path = Path(tempfile.mkdtemp()) / name
        exif = Image.Exif()
        exif[274] = orientation
        Image.new("RGB", size, (30, 150, 50)).save(path, fmt, **({"exif": exif} if fmt == "JPEG" else {}))
        return path

    def size(self, path):
        with Image.open(path) as im:
            return im.size

    def test_a_big_photo_is_shrunk_to_1280(self):
        path = self.make("big.jpg", (4000, 3000))
        imaging.shrink_in_place(path)
        self.assertEqual(self.size(path), (1280, 960))

    def test_the_camera_rotation_is_baked_in(self):
        path = self.make("phone.jpg", (4000, 3000), orientation=6)
        imaging.shrink_in_place(path)
        self.assertEqual(self.size(path), (960, 1280))
        with Image.open(path) as im:
            self.assertEqual(im.getexif().get(274, 1), 1)

    def test_a_small_photo_is_left_alone(self):
        path = self.make("small.jpg", (800, 600))
        before = path.read_bytes()
        imaging.shrink_in_place(path)
        self.assertEqual(path.read_bytes(), before)

    def test_png_stays_png(self):
        path = self.make("big.png", (3000, 2000), fmt="PNG")
        imaging.shrink_in_place(path)
        with Image.open(path) as im:
            self.assertEqual((im.format, im.size), ("PNG", (1280, 853)))

    def test_a_broken_file_never_raises(self):
        path = Path(tempfile.mkdtemp()) / "broken.jpg"
        path.write_bytes(b"not an image")
        with self.assertLogs("cropguard.imaging", level="WARNING"):
            imaging.shrink_in_place(path)
