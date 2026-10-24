@echo off
setlocal
chcp 936 >nul

rem 机器级注册：写入 HKEY_CLASSES_ROOT，需要管理员权限，对整台电脑的所有用户生效。
rem 个人电脑一般用同目录的 register_protocol.bat（当前用户，无需管理员）即可。

rem 当前 bat 所在目录，末尾带反斜杠
set "DIR=%~dp0"
set "BAT=%DIR%start_map.bat"

if not exist "%BAT%" (
    echo [error] start_map.bat not found in %DIR%
    pause
    exit /b 1
)

rem 注册表命令里路径要双写反斜杠
set "BAT_ESC=%BAT:\=\\%"

> "%TEMP%\mcbackup_protocol.reg" (
    echo Windows Registry Editor Version 5.00
    echo.
    echo [HKEY_CLASSES_ROOT\mcbackup]
    echo "URL Protocol"=""
    echo @="MC Backup Launcher"
    echo.
    echo [HKEY_CLASSES_ROOT\mcbackup\shell\open\command]
    echo @="\"%BAT_ESC%\" \"%%1\""
)

reg import "%TEMP%\mcbackup_protocol.reg"
if errorlevel 1 (
    echo [error] 注册失败，请以管理员身份运行
    del "%TEMP%\mcbackup_protocol.reg" >nul 2>nul
    pause
    exit /b 1
)
del "%TEMP%\mcbackup_protocol.reg" >nul 2>nul

echo 已注册 mcbackup:// 协议（整机，所有用户）-^> %BAT%
echo 撤销注册（需管理员）：reg delete "HKLM\Software\Classes\mcbackup" /f
pause
endlocal
