# -*- mode: python ; coding: utf-8 -*-
# PyInstaller onedir 打包配置：产出 dist/PartialBackuper/PartialBackuper.exe
import os

ROOT = SPECPATH
MAP_SELECTOR = os.path.join(ROOT, "map_selector")
ICON = os.path.join(MAP_SELECTOR, "app.ico")

a = Analysis(
    [os.path.join(MAP_SELECTOR, "desktop.py")],
    pathex=[ROOT, MAP_SELECTOR],
    binaries=[],
    datas=[
        (os.path.join(MAP_SELECTOR, "public"), "public"),
        (ICON, "."),
        (os.path.join(ROOT, "global_config.json"), "."),
    ],
    hiddenimports=[
        "server",
        "renderer",
        "backup_runner",
        "script",
        "webview.platforms.edgechromium",
        "webview.platforms.winforms",
        "webview.js",
        "clr",
        "proxy_tools",
        "bottle",
        "tkinter",
        "tkinter.filedialog",
        "tkinter.messagebox",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PartialBackuper",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon=ICON,
)

coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="PartialBackuper")
