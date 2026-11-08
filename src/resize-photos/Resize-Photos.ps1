# Makes email-sized copies of every photo in one folder.
# Runs on the Windows PowerShell 5.1 included with Windows. Keep this file ASCII,
# because PowerShell 5.1 misreads UTF-8 files that have no byte order mark.

param(
    [string]$Folder = '',
    [ValidateRange(16, 20000)][int]$MaxSide = 2000,
    [ValidateRange(1, 100)][int]$Quality = 85
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

# A PowerShell loop over millions of pixels takes seconds per photo, so the scan is compiled.
Add-Type -ReferencedAssemblies System.Drawing -TypeDefinition @'
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;

public static class ResizePhotosPixels
{
    public static bool HasTransparentPixel(Bitmap bitmap)
    {
        Rectangle area = new Rectangle(0, 0, bitmap.Width, bitmap.Height);
        BitmapData data = bitmap.LockBits(area, ImageLockMode.ReadOnly, PixelFormat.Format32bppArgb);
        try
        {
            byte[] row = new byte[bitmap.Width * 4];
            for (int y = 0; y < bitmap.Height; y++)
            {
                Marshal.Copy(IntPtr.Add(data.Scan0, y * data.Stride), row, 0, row.Length);
                for (int alpha = 3; alpha < row.Length; alpha += 4)
                {
                    if (row[alpha] != 255) { return true; }
                }
            }
            return false;
        }
        finally
        {
            bitmap.UnlockBits(data);
        }
    }
}
'@

$PropertyOrientation = 0x0112
$PropertyColorProfile = 0x8773
$OutputFolderName = 'resized'
$EmailLimitBytes = 20MB
$SupportedExtensions = '.jpg', '.jpeg', '.jfif', '.png', '.bmp', '.tif', '.tiff'
$UnsupportedExtensions = '.heic', '.heif', '.webp', '.avif', '.gif'

function Select-PhotoFolder {
    Add-Type -AssemblyName System.Windows.Forms
    $owner = New-Object System.Windows.Forms.Form -Property @{ TopMost = $true }
    $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $dialog.Description = 'Choose the folder of photos to resize'
    try {
        if ($dialog.ShowDialog($owner) -eq [System.Windows.Forms.DialogResult]::OK) {
            return $dialog.SelectedPath
        }
        return ''
    }
    finally {
        $dialog.Dispose()
        $owner.Dispose()
    }
}

function Format-Megabytes([long]$Bytes) {
    return '{0:N1} MB' -f ($Bytes / 1MB)
}

function Get-UniqueName([string]$BaseName, [string]$Extension, $Claimed) {
    $name = $BaseName + $Extension
    $suffix = 2
    while (-not $Claimed.Add($name)) {
        $name = '{0}_{1}{2}' -f $BaseName, $suffix, $Extension
        $suffix++
    }
    return $name
}

function Set-UprightOrientation($Image) {
    if ($Image.PropertyIdList -notcontains $PropertyOrientation) { return }
    $value = $Image.GetPropertyItem($PropertyOrientation).Value
    if ($value.Length -lt 2) { return }
    $flip = switch ([BitConverter]::ToUInt16($value, 0)) {
        2 { 'RotateNoneFlipX' }
        3 { 'Rotate180FlipNone' }
        4 { 'Rotate180FlipX' }
        5 { 'Rotate90FlipX' }
        6 { 'Rotate90FlipNone' }
        7 { 'Rotate270FlipX' }
        8 { 'Rotate270FlipNone' }
    }
    if ($flip) { $Image.RotateFlip([System.Drawing.RotateFlipType]$flip) }
}

function Save-Jpeg($Bitmap, [string]$Path) {
    $parameters = New-Object System.Drawing.Imaging.EncoderParameters(1)
    $parameters.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter(
        [System.Drawing.Imaging.Encoder]::Quality, [long]$Quality)
    try {
        $Bitmap.Save($Path, $JpegCodec, $parameters)
    }
    finally {
        $parameters.Dispose()
    }
}

function Convert-Photo($Source, [string]$OutputFolder, $Claimed) {
    $stream = $null; $image = $null; $canvas = $null; $graphics = $null; $attributes = $null
    $temporary = $null
    try {
        $stream = [System.IO.File]::OpenRead($Source.FullName)
        $image = [System.Drawing.Image]::FromStream($stream, $false, $false)
        Set-UprightOrientation $image

        $longest = [Math]::Max($image.Width, $image.Height)
        $scale = [Math]::Min(1.0, $MaxSide / $longest)
        $width = [Math]::Max(1, [int][Math]::Round($image.Width * $scale))
        $height = [Math]::Max(1, [int][Math]::Round($image.Height * $scale))
        $resized = $scale -lt 1.0

        $hasAlphaFlag = ($image.Flags -band [int][System.Drawing.Imaging.ImageFlags]::HasAlpha) -ne 0
        $pixelFormat = if ($hasAlphaFlag) { 'Format32bppArgb' } else { 'Format24bppRgb' }
        $canvas = New-Object System.Drawing.Bitmap($width, $height,
            [System.Drawing.Imaging.PixelFormat]$pixelFormat)
        $graphics = [System.Drawing.Graphics]::FromImage($canvas)
        $graphics.CompositingMode = [System.Drawing.Drawing2D.CompositingMode]::SourceCopy
        $graphics.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
        $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
        $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality

        # Without the mirrored wrap mode, the resampler blends a pale fringe into the image edges.
        $attributes = New-Object System.Drawing.Imaging.ImageAttributes
        $attributes.SetWrapMode([System.Drawing.Drawing2D.WrapMode]::TileFlipXY)
        $destination = New-Object System.Drawing.Rectangle(0, 0, $width, $height)
        $graphics.DrawImage($image, $destination, 0, 0, $image.Width, $image.Height,
            [System.Drawing.GraphicsUnit]::Pixel, $attributes)

        if ($image.PropertyIdList -contains $PropertyColorProfile) {
            $canvas.SetPropertyItem($image.GetPropertyItem($PropertyColorProfile))
        }

        $keepPng = $hasAlphaFlag -and [ResizePhotosPixels]::HasTransparentPixel($canvas)
        $extension = if ($keepPng) { '.png' } else { '.jpg' }
        $outputName = Get-UniqueName $Source.BaseName $extension $Claimed
        $outputPath = Join-Path $OutputFolder $outputName
        $temporary = $outputPath + '.tmp'

        if ($keepPng) {
            $canvas.Save($temporary, [System.Drawing.Imaging.ImageFormat]::Png)
        }
        else {
            Save-Jpeg $canvas $temporary
        }

        $sourceExtension = $Source.Extension.ToLowerInvariant()
        $sameFormat = if ($keepPng) { $sourceExtension -eq '.png' } else { $sourceExtension -in '.jpg', '.jpeg', '.jfif' }
        $grew = (Get-Item -LiteralPath $temporary).Length -ge $Source.Length
        if ($sameFormat -and -not $resized -and $grew) {
            [System.IO.File]::Copy($Source.FullName, $temporary, $true)
        }

        if ([System.IO.File]::Exists($outputPath)) { [System.IO.File]::Delete($outputPath) }
        [System.IO.File]::Move($temporary, $outputPath)
        $temporary = $null
        [System.IO.File]::SetLastWriteTimeUtc($outputPath, $Source.LastWriteTimeUtc)

        return [PSCustomObject]@{
            Name   = $outputName
            Length = (Get-Item -LiteralPath $outputPath).Length
        }
    }
    finally {
        foreach ($item in $attributes, $graphics, $canvas, $image, $stream) {
            if ($null -ne $item) { $item.Dispose() }
        }
        if ($temporary -and [System.IO.File]::Exists($temporary)) {
            [System.IO.File]::Delete($temporary)
        }
    }
}

# A dragged drive root arrives as D:" because the trailing backslash escapes the closing quote.
$Folder = $Folder.Trim().Trim('"')
if ($Folder -match '^[A-Za-z]:$') { $Folder += '\' }

if (-not $Folder) {
    $Folder = Select-PhotoFolder
    if (-not $Folder) {
        Write-Host 'No folder chosen. Nothing was changed.'
        exit 0
    }
}

if (-not (Test-Path -LiteralPath $Folder -PathType Container)) {
    Write-Host "This is not a folder: $Folder"
    Write-Host 'Drag a whole folder of photos onto Resize-Photos.bat.'
    exit 1
}

$Folder = (Get-Item -LiteralPath $Folder).FullName
$JpegCodec = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() |
    Where-Object { $_.MimeType -eq 'image/jpeg' }

$files = @(Get-ChildItem -LiteralPath $Folder -File | Sort-Object Name)
$photos = @($files | Where-Object { $SupportedExtensions -contains $_.Extension.ToLowerInvariant() })
$notConverted = @($files | Where-Object { $UnsupportedExtensions -contains $_.Extension.ToLowerInvariant() })

if ($photos.Count -eq 0) {
    Write-Host "No JPG, PNG, BMP or TIFF photos were found in: $Folder"
    foreach ($file in $notConverted) { Write-Host "  Not converted (unsupported format): $($file.Name)" }
    exit 1
}

$outputFolder = Join-Path $Folder $OutputFolderName
[void][System.IO.Directory]::CreateDirectory($outputFolder)

Write-Host "Resizing $($photos.Count) photo(s) from: $Folder"
Write-Host "Copies go to: $outputFolder"
Write-Host ''

$claimed = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)
$failed = New-Object System.Collections.Generic.List[string]
[long]$totalBefore = 0
[long]$totalAfter = 0
$made = 0
$position = 0

foreach ($photo in $photos) {
    $position++
    $counter = '[{0}/{1}]' -f $position, $photos.Count
    try {
        $result = Convert-Photo $photo $outputFolder $claimed
        $made++
        $totalBefore += $photo.Length
        $totalAfter += $result.Length
        Write-Host "$counter $($photo.Name)   $(Format-Megabytes $photo.Length) -> $(Format-Megabytes $result.Length)"
    }
    catch {
        $failed.Add($photo.Name)
        Write-Host "$counter $($photo.Name)   COULD NOT BE READ, skipped"
    }
}

Write-Host ''
Write-Host "Done. $made photo(s) made: $(Format-Megabytes $totalBefore) -> $(Format-Megabytes $totalAfter)"
if ($totalAfter -gt $EmailLimitBytes) {
    $emails = [int][Math]::Ceiling($totalAfter / $EmailLimitBytes)
    Write-Host "Email services allow about 20 MB per message, so plan on about $emails emails."
}
foreach ($name in $failed) { Write-Host "Could not be read: $name" }
foreach ($file in $notConverted) { Write-Host "Not converted (unsupported format): $($file.Name)" }

if ($made -gt 0 -and -not $env:RESIZE_PHOTOS_NO_OPEN) {
    Invoke-Item -LiteralPath $outputFolder
}

if ($failed.Count -gt 0) { exit 1 }
exit 0
