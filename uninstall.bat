@echo off
setlocal EnableExtensions
chcp 936 >nul
title MC存档选区备份工具 - 卸载

set "ROOT=%~dp0"
cd /d "%ROOT%"

echo ==============================================
echo  MC存档选区备份工具 - 卸载
echo ==============================================
echo.
echo 将执行：
echo   1. 清理 mcbackup:// 协议注册（当前用户；有管理员权限时同时清理整机）
echo   2. 删除程序文件（服务端、网页界面、启动与注册脚本、说明文档）
echo   3. 保留你的数据：configs\、global_config.json、
echo      map_selector\world.json、map_selector\.cache\
echo      以及各存档目录里的备份 zip
echo.
echo 不会删除 .git（如果存在）和自己放入的其它文件。
echo 建议先关闭正在运行的服务窗口和已打开的页面。
echo.
set "ANSWER="
set /p "ANSWER=输入 yes 并回车以确认卸载（其它输入取消）："
if /i not "%ANSWER%"=="yes" (
    echo.
    echo 已取消，未做任何修改。
    pause
    exit /b 0
)

echo.
echo [1/3] 清理协议注册
reg query "HKCU\Software\Classes\mcbackup" >nul 2>nul
if errorlevel 1 (
    echo   [skip] 当前用户未注册 mcbackup://
) else (
    reg delete "HKCU\Software\Classes\mcbackup" /f >nul 2>nul
    if errorlevel 1 (
        echo   [warn] 当前用户注册清理失败
    ) else (
        echo   [ok] 已清理当前用户的 mcbackup:// 注册
    )
)

reg query "HKLM\Software\Classes\mcbackup" >nul 2>nul
if errorlevel 1 (
    echo   [skip] 整机未注册 mcbackup://
) else (
    reg delete "HKLM\Software\Classes\mcbackup" /f >nul 2>nul
    if errorlevel 1 (
        echo   [warn] 整机注册需要管理员权限，未能清理
        echo          如曾运行过 register_protocol_admin.bat，请右键以管理员身份重新运行本脚本
    ) else (
        echo   [ok] 已清理整机 mcbackup:// 注册
    )
)

echo.
echo [2/3] 删除 PWA 快捷方式
if exist "map_selector\app.lnk" (
    del /f /q "map_selector\app.lnk" >nul 2>nul
    if exist "map_selector\app.lnk" (
        echo   [warn] app.lnk 删除失败
    ) else (
        echo   [ok] 已删除 map_selector\app.lnk
    )
) else (
    echo   [skip] 没有 app.lnk
)

echo.
echo [3/3] 删除程序文件
for %%F in (
    ".gitignore"
    "LICENSE"
    "NOTICE"
    "README.md"
    "backup_runner.py"
    "script.py"
    "requirements.txt"
    "run_script.bat"
    "start_map.bat"
    "map_selector\server.py"
    "map_selector\renderer.py"
    "map_selector\start_map.bat"
    "map_selector\register_protocol.bat"
    "map_selector\register_protocol_admin.bat"
) do (
    if exist "%%~F" del /f /q "%%~F" >nul 2>nul
)
for %%D in ("__pycache__" "map_selector\__pycache__" "map_selector\public") do (
    if exist "%%~D" rd /s /q "%%~D" >nul 2>nul
)

set "LEFT="
if exist "map_selector\server.py" set "LEFT=1"
if exist "map_selector\public" set "LEFT=1"
if exist "start_map.bat" set "LEFT=1"
if defined LEFT (
    echo   [warn] 部分文件未能删除，可能正被占用
    echo          请关闭服务窗口和浏览器页面后，重新运行本脚本（脚本已保留）
) else (
    echo   [ok] 程序文件已删除
)

if exist ".git" echo   [info] 检测到 .git 目录，属于源码仓库，未删除

echo.
echo ==============================================
if defined LEFT (
    echo  卸载未完全完成，请处理后重试
) else (
    echo  卸载完成
)
echo ==============================================
echo.
echo 以下数据已保留，如不再需要可自行删除：
echo   - 备份配置：%ROOT%configs\
echo   - 全局配置：%ROOT%global_config.json
echo   - 上次打开的存档：%ROOT%map_selector\world.json
echo   - 地图瓦片缓存：%ROOT%map_selector\.cache\
echo   - 各存档目录里的备份 zip（不在本目录，未做任何改动）
echo   - 浏览器里安装的 PWA：需在 Edge/Chrome 的“应用”页面手动卸载
if exist "map_selector_static" echo   - map_selector_static\（未完成的实验目录，保留未删）
echo.
echo 如需彻底清除，直接删除整个文件夹：
echo   %ROOT%
echo.
pause

if defined LEFT goto cleanup_done
(goto) 2>nul & del /f /q "%~f0" >nul 2>nul
:cleanup_done
endlocal
