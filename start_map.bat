@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

rem Detect a Python interpreter. Control-flow lines stay ASCII-only so cmd parses
rem them even if the console codepage differs from this file encoding. The only
rem Chinese text cmd reads on a successful launch is the window title below.
where python >nul 2>nul && (set "RUN=python" & goto run)
where py >nul 2>nul && (set "RUN=py -3" & goto run)
echo [error] Python 3 not found. Install Python 3 and add it to PATH, then retry.
pause
exit /b 1

:run
rem Launch the map selector tool. server.py resolves its own paths from __file__,
rem so /D just points the child console into map_selector. The server runs in its
rem own window: Ctrl+C stops it without a batch prompt, and /c closes on a clean
rem exit; server.py waits for a keypress if startup fails so a crash stays visible.
start "MC存档选区备份工具" /D "%~dp0map_selector" cmd /c %RUN% server.py %*
endlocal
