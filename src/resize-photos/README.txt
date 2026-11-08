RESIZE PHOTOS

Makes smaller copies of your photos so they fit in an email.
Your original photos are not changed. Works on Windows 10 and 11.
There is nothing to install.


HOW TO USE

1. If these files arrived in a zip, right-click the zip and choose
   "Extract All". The program does not run from inside a zip.

2. Drag your folder of photos onto Resize-Photos.bat.
   Or double-click Resize-Photos.bat and choose the folder.

3. If a blue "Windows protected your PC" box appears, click
   "More info", then "Run anyway".

4. A black window lists each photo as it is done. When it finishes,
   a new folder named "resized" opens inside your photo folder.

5. Attach the photos from the "resized" folder to your email.
   Press any key in the black window to close it.


WHAT YOU GET

- Photos are at most 2000 pixels on their longest side.
- Photos are saved as JPG at quality 85.
- Images with transparent areas stay PNG.
- Smaller photos are not enlarged.
- Running it again replaces the earlier copies in "resized".


GOOD TO KNOW

- Only photos directly in the chosen folder are done, not ones in
  folders inside it.
- Resized copies do not keep camera details, such as the date taken or
  the location. A photo that was already small may be copied as it is,
  and keeps its details.
- JPG, PNG, BMP and TIFF files are supported.
- HEIC, WebP, AVIF and GIF files are listed at the end as
  "Not converted".
- Email services allow about 20 MB per message. The window tells you
  about how many emails you need.


DIFFERENT SIZE OR QUALITY

Open PowerShell in this folder and run a command like this one:

  powershell -ExecutionPolicy Bypass -File .\Resize-Photos.ps1 "path\to\photos" -MaxSide 1600 -Quality 80
