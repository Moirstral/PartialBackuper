@echo off
setlocal
chcp 936 >nul

rem 用户级注册：只写 HKEY_CURRENT_USER，不需要管理员权限，仅当前 Windows 用户生效。
rem 若要多用户共用同一份工具，改用同目录的 register_protocol_admin.bat（需管理员）。
rem 用法：
rem   register_protocol.bat             注册
rem   register_protocol.bat unregister  撤销注册

set "KEY=HKCU\Software\Classes\mcbackup"

if /i "%~1"=="unregister" goto unregister

rem 当前 bat 所在目录，末尾带反斜杠
set "DIR=%~dp0"
set "BAT=%DIR%start_map.bat"

if not exist "%BAT%" (
    echo [error] start_map.bat not found in %DIR%
    pause
    exit /b 1
)

reg add "%KEY%" /ve /d "MC Backup Launcher" /f >nul 2>nul
if errorlevel 1 goto failed
reg add "%KEY%" /v "URL Protocol" /t REG_SZ /d "" /f >nul 2>nul
if errorlevel 1 goto failed
reg add "%KEY%\shell\open\command" /ve /d "\"%BAT%\" \"%%1\"" /f >nul 2>nul
if errorlevel 1 goto failed

echo 已注册 mcbackup:// 协议（仅当前用户，无需管理员）
echo   启动脚本：%BAT%
echo   撤销注册：register_protocol.bat unregister
pause
exit /b 0

:unregister
reg delete "%KEY%" /f >nul 2>nul
if errorlevel 1 (
    echo 当前用户下没有 mcbackup:// 注册，无需撤销。
) else (
    echo 已撤销当前用户的 mcbackup:// 注册。
)
pause
exit /b 0

:failed
echo [error] 注册失败（错误码 %errorlevel%）。
pause
exit /b 1
