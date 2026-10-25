@echo off
setlocal
chcp 65001 >nul

rem Desktop entry point: map_selector\start_map.bat launches desktop.py, which opens
rem the app window and runs the local backend inside the same process.
call "%~dp0map_selector\start_map.bat" %*
endlocal
