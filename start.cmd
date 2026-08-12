@echo off
setlocal

REM Double-click this file, or run: .\start.cmd
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-dev.ps1" %*
if errorlevel 1 (
    echo.
    echo Startup failed. See the message above, then press any key to close.
    pause >nul
)

endlocal
