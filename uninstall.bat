@echo off
setlocal EnableExtensions
chcp 65001 >nul
title MC存档选区备份工具 - 卸载

set "ROOT=%~dp0"
cd /d "%ROOT%"

echo ==============================================
echo  MC存档选区备份工具 - 卸载
echo ==============================================
echo.
echo 将执行：
echo   1. 删除桌面快捷方式残留（app.lnk，如果存在）
echo   2. 删除程序文件（后端、桌面入口、前端、启动与打包脚本、说明文档）
echo   3. 删除打包产物 dist\ 与 build\（如果构建过 exe）
echo.
echo 不会删除：
echo   - 备份配置 configs\ 与全局设置 global_config.json
echo   - 桌面版数据目录 UserData\（瓦片缓存、上次存档、WebView 配置）
echo     和 %%APPDATA%%\PartialBackuper
echo   - 存档目录旁的备份 zip
echo   - .git（若这是源码仓库）
echo.
echo 请先关闭已经打开的软件窗口，否则文件被占用会删不掉。
echo.
set "ANSWER="
set /p "ANSWER=输入 yes 并回车以确认卸载，其他任意内容取消："
if /i not "%ANSWER%"=="yes" (
    echo.
    echo 已取消，未做任何修改。
    pause
    exit /b 0
)

echo.
echo [1/3] 清理桌面快捷方式残留
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
echo [2/3] 删除程序文件
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
    "build_exe.bat"
    "PartialBackuper.spec"
    "map_selector\desktop.py"
    "map_selector\server.py"
    "map_selector\renderer.py"
    "map_selector\start_map.bat"
) do (
    if exist "%%~F" del /f /q "%%~F" >nul 2>nul
)
for %%D in ("__pycache__" "map_selector\__pycache__" "map_selector\public" "dist" "build") do (
    if exist "%%~D" rd /s /q "%%~D" >nul 2>nul
)

set "LEFT="
if exist "map_selector\server.py" set "LEFT=1"
if exist "map_selector\public" set "LEFT=1"
if exist "start_map.bat" set "LEFT=1"
if defined LEFT (
    echo   [warn] 部分文件未能删除，通常是程序还在运行
    echo          请关闭软件窗口后重新运行本脚本；脚本会自动跳过已删除的文件
) else (
    echo   [ok] 程序文件已删除
)

if exist ".git" echo   [info] 检测到 .git 目录：这是源码仓库，未删除

echo.
echo [3/3] 卸载完成
echo ==============================================
echo.
echo 以下用户数据已保留，如不需要请自行删除：
echo   - 备份配置：%ROOT%configs\
echo   - 全局设置：%ROOT%global_config.json
echo   - 便携数据目录：%ROOT%UserData\
echo   - 系统数据目录：%APPDATA%\PartialBackuper
echo     （其中 webview\ 子目录是页面本地存储，保存「仅浏览器配置」与红叉排除标记）
echo   - 各存档目录旁的备份 zip（不在本目录，未做任何改动）
echo.
echo 如需彻底清理，直接删除整个程序文件夹：
echo   %ROOT%
echo.
pause

if defined LEFT goto cleanup_done
(goto) 2>nul & del /f /q "%~f0" >nul 2>nul
:cleanup_done
endlocal
