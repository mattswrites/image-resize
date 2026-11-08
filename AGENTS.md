# image-resize

A drag-and-drop package for Windows that makes email-sized copies of a folder of photos. It installs nothing on the computer that runs it. The product is a zip of three files: a `.bat` launcher, a PowerShell script and a plain-text README for the person using it.

## Stack and layout

The product in `src/resize-photos/` uses only Windows PowerShell 5.1 and .NET System.Drawing, both included with Windows. Python and Pillow are development tools only, used by `scripts/build_package.py` and `tests/`.

## Commands

```
python scripts/build_package.py
python -m unittest discover -s tests
```

The first command writes the zip to the git-excluded `dist` folder. The tests need Windows and Pillow. They build the zip, extract it and run the extracted `.bat` on generated images.

## Conventions

- `Resize-Photos.ps1` stays ASCII, because PowerShell 5.1 reads a UTF-8 file with no byte order mark as ANSI. The build fails on any non-ASCII byte.
- Line endings are converted to CRLF at build time, because `cmd.exe` can misread LF batch files.
- Test through `Resize-Photos.bat` and `powershell.exe`, because that is the path the product runs on. PowerShell 7 behaves differently.
- Output defaults are a longest side of 2000 pixels and JPG quality 85. Images with transparent pixels stay PNG.

## Gotchas

- System.Drawing ignores the EXIF orientation tag and the copies do not keep it, so `Set-UprightOrientation` rotates the pixels before resizing.
- System.Drawing cannot decode HEIC, HEIF, WebP or AVIF. The script lists those files as not converted.
- Motion photos store an MP4 after the JPEG end marker. Re-encoding drops it, and the copy-unchanged branch is skipped for any file with data after the image, so that branch cannot carry a video into the output.
- Use `-LiteralPath` and `[System.IO.File]` for file access, because `[` and `]` in photo names are wildcards to most PowerShell cmdlets.
- A dragged drive root reaches the script as `D:"`, because the trailing backslash escapes the closing quote. The script repairs that value.
- `RESIZE_PHOTOS_NO_OPEN=1` stops the script opening Explorer. The tests set it.
- Common mail services reject attachments containing `.bat` or `.ps1` files, even inside a zip. Move the package by USB drive or a cloud storage link.
