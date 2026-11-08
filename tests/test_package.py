"""End-to-end tests: build the zip, extract it, run the .bat on synthetic images.

Requires Windows and Pillow. Run with: python -m unittest discover -s tests
"""

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image, ImageCms

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import build_package  # noqa: E402

ORIENTATION_TAG = 0x0112
OLD_TIME = 1_500_000_000
FAKE_VIDEO = b"\x00\x00\x00\x18ftypmp42fake video data"
MOTION_XMP = b'<x:xmpmeta xmlns:x="adobe:ns:meta/" GCamera:MotionPhoto="1"/>'


def noise(width, height):
    gray = Image.effect_noise((width, height), 40).convert("RGB")
    return gray


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_package(bat, folder):
    environment = dict(os.environ, RESIZE_PHOTOS_NO_OPEN="1")
    return subprocess.run(
        f'"{bat}" "{folder}"',
        shell=True,
        env=environment,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=300,
    )


def make_fixtures(folder):
    folder.mkdir(parents=True)
    noise(3000, 4000).save(folder / "portrait.jpg", quality=97)
    noise(4000, 3000).save(folder / "landscape.JPEG", quality=97)
    noise(800, 600).save(folder / "small.jpg", quality=97)
    noise(1000, 1000).save(folder / "already_compressed.jpg", quality=20)

    rotated = Image.new("RGB", (4000, 3000), (0, 0, 255))
    rotated.paste((255, 0, 0), (0, 0, 2000, 3000))
    exif = Image.Exif()
    exif[ORIENTATION_TAG] = 6
    rotated.save(folder / "rotated.jpg", quality=95, exif=exif)

    Image.new("RGBA", (3000, 4000), (10, 120, 200, 255)).save(folder / "opaque_rgba.png")

    transparent = Image.new("RGBA", (3000, 4000), (200, 30, 30, 255))
    transparent.paste((0, 0, 0, 0), (0, 0, 1500, 2000))
    transparent.save(folder / "transparent.png")

    palette = Image.new("P", (2400, 3000), 1)
    palette.putpalette([0, 0, 0, 255, 0, 0])
    palette.paste(0, (0, 0, 1200, 1500))
    palette.save(folder / "palette.png", transparency=0)

    Image.new("RGB", (600, 400), (0, 200, 0)).save(folder / "twin.jpg")
    Image.new("RGB", (600, 400), (0, 0, 200)).save(folder / "twin.png")

    profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    noise(3000, 2000).save(folder / "profiled.jpg", quality=95, icc_profile=profile)

    noise(3000, 4000).save(folder / "motion.jpg", quality=90, xmp=MOTION_XMP)
    with open(folder / "motion.jpg", "ab") as photo:
        photo.write(FAKE_VIDEO + bytes(2_000_000))

    noise(1000, 1000).save(folder / "small_motion.jpg", quality=20)
    with open(folder / "small_motion.jpg", "ab") as photo:
        photo.write(FAKE_VIDEO)

    noise(1000, 1000).save(folder / "progressive.jpg", quality=20, progressive=True)
    noise(1000, 1000).save(folder / "marker_in_comment.jpg", quality=20, comment=b"\xff\xd9 not the end")

    (folder / "[beach] 100% & sun.jpg").write_bytes((folder / "small.jpg").read_bytes())
    (folder / "phone.heic").write_bytes(b"not decodable here")
    (folder / "broken.jpg").write_bytes(b"this is not a photo")
    (folder / "notes.txt").write_text("not an image")
    os.utime(folder / "portrait.jpg", (OLD_TIME, OLD_TIME))


class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = Path(tempfile.mkdtemp(prefix="resize-test-"))
        zip_path = build_package.build(cls.work / "package.zip")
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(cls.work / "extracted")
        cls.package = cls.work / "extracted" / "resize-photos"
        cls.bat = cls.package / "Resize-Photos.bat"

        cls.folder = cls.work / "photos"
        make_fixtures(cls.folder)
        cls.before = {p.name: digest(p) for p in cls.folder.iterdir() if p.is_file()}
        cls.result = run_package(cls.bat, cls.folder)
        cls.output = cls.folder / "resized"

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work, ignore_errors=True)

    def open(self, name):
        path = self.output / name
        self.assertTrue(path.exists(), f"{name} missing. Output:\n{self.result.stdout}")
        return Image.open(path)

    def test_zip_files_use_crlf(self):
        for name in build_package.PACKAGE_FILES:
            data = (self.package / name).read_bytes()
            self.assertEqual(data.count(b"\n"), data.count(b"\r\n"), name)

    def test_portrait_is_scaled_to_longest_side(self):
        with self.open("portrait.jpg") as image:
            self.assertEqual(image.size, (1500, 2000))
            self.assertEqual(image.format, "JPEG")

    def test_landscape_uppercase_extension_becomes_jpg(self):
        with self.open("landscape.jpg") as image:
            self.assertEqual(image.size, (2000, 1500))

    def test_small_photo_is_not_enlarged(self):
        with self.open("small.jpg") as image:
            self.assertEqual(image.size, (800, 600))

    def test_exif_rotation_is_applied_to_pixels(self):
        with self.open("rotated.jpg") as image:
            self.assertEqual(image.size, (1500, 2000))
            self.assertNotEqual(image.getexif().get(ORIENTATION_TAG), 6)
            top = image.convert("RGB").getpixel((750, 100))
            bottom = image.convert("RGB").getpixel((750, 1900))
        self.assertGreater(top[0], 200)
        self.assertGreater(bottom[2], 200)

    def test_opaque_png_becomes_jpg(self):
        with self.open("opaque_rgba.jpg") as image:
            self.assertEqual(image.format, "JPEG")
            self.assertEqual(image.size, (1500, 2000))
        self.assertFalse((self.output / "opaque_rgba.png").exists())

    def test_transparent_png_stays_png_with_alpha(self):
        with self.open("transparent.png") as image:
            self.assertEqual(image.format, "PNG")
            self.assertEqual(image.size, (1500, 2000))
            rgba = image.convert("RGBA")
            self.assertEqual(rgba.getpixel((100, 100))[3], 0)
            self.assertEqual(rgba.getpixel((1400, 1900))[3], 255)

    def test_palette_transparency_stays_png(self):
        with self.open("palette.png") as image:
            self.assertEqual(image.convert("RGBA").getpixel((100, 100))[3], 0)

    def test_name_collision_keeps_both(self):
        names = {p.name for p in self.output.iterdir()}
        self.assertIn("twin.jpg", names)
        self.assertIn("twin_2.jpg", names)

    def test_color_profile_is_kept(self):
        with self.open("profiled.jpg") as image:
            self.assertTrue(image.info.get("icc_profile"))

    def test_modified_time_is_kept(self):
        self.assertEqual(int((self.output / "portrait.jpg").stat().st_mtime), OLD_TIME)

    def test_file_that_would_grow_is_copied_unchanged(self):
        self.assertEqual(
            digest(self.output / "already_compressed.jpg"),
            digest(self.folder / "already_compressed.jpg"),
        )

    def assert_still_photo(self, name):
        data = (self.output / name).read_bytes()
        self.assertNotIn(b"ftyp", data, name)
        self.assertNotIn(b"MotionPhoto", data, name)
        self.assertTrue(data.endswith(b"\xff\xd9"), name)

    def test_motion_video_is_removed_from_resized_copy(self):
        self.assert_still_photo("motion.jpg")
        with self.open("motion.jpg") as image:
            self.assertEqual(image.size, (1500, 2000))
        self.assertRegex(self.result.stdout, r"motion\.jpg .*\(motion video removed\)")

    def test_motion_video_is_removed_when_photo_would_grow(self):
        self.assert_still_photo("small_motion.jpg")
        self.assertRegex(self.result.stdout, r"small_motion\.jpg .*\(motion video removed\)")
        self.assertIn("Motion videos removed from the copies: 2", self.result.stdout)

    def test_original_motion_photo_keeps_its_video(self):
        self.assertIn(FAKE_VIDEO, (self.folder / "motion.jpg").read_bytes())

    def test_still_photos_are_not_mistaken_for_motion_photos(self):
        for name in ("progressive.jpg", "marker_in_comment.jpg"):
            self.assertEqual(digest(self.output / name), digest(self.folder / name), name)

    def test_special_characters_in_file_name(self):
        self.assertTrue((self.output / "[beach] 100% & sun.jpg").exists())

    def test_originals_are_untouched(self):
        now = {p.name: digest(p) for p in self.folder.iterdir() if p.is_file()}
        self.assertEqual(now, self.before)

    def test_no_temporary_files_left(self):
        self.assertEqual([p.name for p in self.output.glob("*.tmp")], [])

    def test_unsupported_and_broken_files_are_reported(self):
        self.assertIn("Not converted (unsupported format): phone.heic", self.result.stdout)
        self.assertIn("Could not be read: broken.jpg", self.result.stdout)
        self.assertFalse((self.output / "broken.jpg").exists())
        self.assertEqual(self.result.returncode, 1)

    def test_running_twice_gives_the_same_names(self):
        first = sorted(p.name for p in self.output.iterdir())
        again = run_package(self.bat, self.folder)
        self.assertIn("Done.", again.stdout)
        self.assertEqual(sorted(p.name for p in self.output.iterdir()), first)
        self.assertFalse((self.output / "resized").exists())

    def test_folder_name_with_special_characters(self):
        folder = self.work / "Trip [2024] 100% & more"
        folder.mkdir()
        Image.new("RGB", (3000, 4000), (9, 9, 9)).save(folder / "a.jpg")
        result = run_package(self.bat, folder)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        with Image.open(folder / "resized" / "a.jpg") as image:
            self.assertEqual(image.size, (1500, 2000))

    def test_launcher_without_script_explains_what_to_do(self):
        alone = self.work / "alone (copy) & here"
        alone.mkdir()
        shutil.copy(self.bat, alone)
        result = run_package(alone / "Resize-Photos.bat", self.folder)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Extract All", result.stdout)
        self.assertNotIn("-File parameter", result.stdout + result.stderr)

    def test_missing_folder_is_reported(self):
        result = run_package(self.bat, self.work / "does-not-exist")
        self.assertEqual(result.returncode, 1)
        self.assertIn("This is not a folder", result.stdout)

    def test_folder_with_no_photos(self):
        folder = self.work / "empty"
        folder.mkdir()
        result = run_package(self.bat, folder)
        self.assertEqual(result.returncode, 1)
        self.assertIn("No JPG, PNG, BMP or TIFF photos", result.stdout)
        self.assertFalse((folder / "resized").exists())


if __name__ == "__main__":
    unittest.main()
