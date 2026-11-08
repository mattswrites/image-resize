@echo off
rem Drag a folder onto this file, or double-click this file and choose a folder.
title Resize Photos
rem Opening this file from inside a zip extracts only this file, so the script is missing.
if not exist "%~dp0Resize-Photos.ps1" (
    echo Resize-Photos.ps1 must be in the same folder as this file.
    echo.
    echo If these files are in a zip, right-click the zip, choose Extract All,
    echo then open the extracted folder and use Resize-Photos.bat from there.
    echo.
    pause
    exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Resize-Photos.ps1" "%~1"
set "RESIZE_EXIT=%ERRORLEVEL%"
echo.
pause
exit /b %RESIZE_EXIT%
