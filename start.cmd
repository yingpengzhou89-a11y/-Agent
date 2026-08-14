@echo off
setlocal
REM Double-click this file, or run: .\start.cmd
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-dev.ps1" %*
echo.
echo Startup finished. You can close this window when you no longer need it.
cmd /k