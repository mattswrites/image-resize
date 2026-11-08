"""Builds the zip that is sent to the Windows computer.

Every file gets CRLF line endings in the zip, because cmd.exe can misread
batch files that use LF. The PowerShell script must be ASCII.
"""

import argparse
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "src" / "resize-photos"
PACKAGE_FILES = ("Resize-Photos.bat", "Resize-Photos.ps1", "README.txt")
DEFAULT_OUTPUT = ROOT / "dist" / "resize-photos.zip"


def build(output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    stamp = time.localtime()[:6]
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in PACKAGE_FILES:
            data = (SOURCE / name).read_bytes()
            data.decode("ascii")
            data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
            entry = zipfile.ZipInfo(f"resize-photos/{name}", date_time=stamp)
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, data)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    print(build(arguments.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
