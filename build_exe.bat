@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

rem Build the desktop folder-exe (onedir) with PyInstaller.
rem Control-flow lines stay ASCII-only so cmd parses them under any codepage.
where pyinstaller >nul 2>nul && (set "BUILD=pyinstaller" & goto build)
where python >nul 2>nul && (set "BUILD=python -m PyInstaller" & goto build)
where py >nul 2>nul && (set "BUILD=py -3 -m PyInstaller" & goto build)
echo [error] PyInstaller not found.
echo [hint]  pip install pywebview pyinstaller
pause
exit /b 1

:build
echo Building dist\PartialBackuper\PartialBackuper.exe ...
%BUILD% --noconfirm --clean PartialBackuper.spec
if errorlevel 1 (
    echo.
    echo [error] build failed
    pause
    exit /b 1
)
echo.
echo [ok] dist\PartialBackuper\PartialBackuper.exe
echo      整个 dist\PartialBackuper 文件夹一起拷贝即可使用。
pause
endlocal
