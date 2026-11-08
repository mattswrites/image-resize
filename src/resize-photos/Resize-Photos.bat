@echo off
rem Drag a folder onto this file, or double-click this file and choose a folder.
title Resize Photos
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Resize-Photos.ps1" "%~1"
set "RESIZE_EXIT=%ERRORLEVEL%"
echo.
pause
exit /b %RESIZE_EXIT%
