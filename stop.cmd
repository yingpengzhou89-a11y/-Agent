@echo off
setlocal

REM Double-click this file, or run: .\stop.cmd
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop-dev.ps1"
if errorlevel 1 pause

endlocal
