@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

rem Detect a Python interpreter. Control-flow lines stay ASCII-only so cmd parses
rem them even if the console codepage differs from this file encoding.
rem pythonw first: the desktop entry opens its own window, so no console is wanted.
where pythonw >nul 2>nul && (set "RUN=pythonw" & goto run)
where python >nul 2>nul && (set "RUN=python" & goto run)
where py >nul 2>nul && (set "RUN=py -3" & goto run)
echo [error] Python 3 not found. Install Python 3 and add it to PATH, then retry.
echo [hint] Desktop window needs pywebview: pip install -r requirements.txt
pause
exit /b 1

:run
rem desktop.py opens the window and runs the local backend inside the same process;
rem closing the window stops everything. Errors are shown in a dialog, so a missing
rem dependency is still visible without a console.
start "" %RUN% "%~dp0desktop.py" %*
endlocal
