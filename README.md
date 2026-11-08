# image-resize

Makes email-sized copies of a folder of photos on Windows 10 or 11, with nothing to install.

Drag a folder onto `Resize-Photos.bat`, or double-click the file and choose a folder. Copies go to a `resized` subfolder, and the originals are not modified.

The package is the three files in `src/resize-photos/`. Copy that folder to the Windows computer and keep the files together.

| Setting | Default |
|---|---|
| Longest side | 2000 pixels, never enlarged |
| Output format | JPG at quality 85, except images with transparent pixels, which stay PNG |
| Input formats | JPG, PNG, BMP, TIFF |
| Folders processed | The chosen folder only |

Copies are rotated upright and keep the color profile and modified date of the original. Other camera metadata, including location, is not copied. A photo that needs no resizing and would grow when re-encoded is copied unchanged, with its metadata, unless the file holds data after the image.

Motion photos become still photos: the video stored after the JPEG image data is left out of the copy, and the console names each photo it was removed from. Separate video files, such as `.MOV` files from iPhone Live Photos, are not copied.

HEIC, HEIF, WebP, AVIF and GIF files are listed as not converted.

Other sizes are set on the command line:

```
powershell -ExecutionPolicy Bypass -File .\Resize-Photos.ps1 "path\to\photos" -MaxSide 1600 -Quality 80
```

## Building

```
python scripts/build_package.py --output resize-photos.zip
python -m unittest discover -s tests
```

The tests need Windows and Pillow.

## License

MIT. See `LICENSE`.
