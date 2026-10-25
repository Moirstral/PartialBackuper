"""MC存档选区备份工具 · 桌面版入口。

双击 exe（或 python desktop.py）即：选/复用数据目录 → 起本地后端 → 开内嵌 WebView2 窗口。
关闭窗口时后端随进程一起退出，不再有浏览器、PWA 与协议拉起。
"""
import json
import multiprocessing
import os
import shutil
import sys
import threading
from pathlib import Path

APP_TITLE = "MC存档选区备份工具"
PORTABLE_DIR_NAME = "UserData"
APPDATA_DIR_NAME = "PartialBackuper"
MARKER_NAME = "storage.json"

FROZEN = getattr(sys, "frozen", False)
BASE_DIR = Path(__file__).resolve().parent
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", BASE_DIR)) if FROZEN else BASE_DIR
PROJECT_DIR = RESOURCE_DIR if FROZEN else BASE_DIR.parent
PROGRAM_DIR = Path(sys.executable).resolve().parent if FROZEN else PROJECT_DIR
LEGACY_WORLD_FILE = BASE_DIR / "world.json"

for _p in (str(RESOURCE_DIR), str(PROJECT_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import server  # noqa: E402  路径就绪后才能导入


def appdata_dir():
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / APPDATA_DIR_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APPDATA_DIR_NAME
    xdg = os.environ.get("XDG_DATA_HOME")
    return (Path(xdg) if xdg else Path.home() / ".local" / "share") / APPDATA_DIR_NAME


def portable_dir():
    return PROGRAM_DIR / PORTABLE_DIR_NAME


def marker_path(root):
    return Path(root) / MARKER_NAME


def has_marker(root):
    try:
        return marker_path(root).is_file()
    except OSError:
        return False


def write_marker(root, mode):
    try:
        marker_path(root).write_text(
            json.dumps({"app": APP_TITLE, "mode": mode}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as e:
        print(f"数据目录标记写入失败：{e}")


def seed_world_file(data_dir):
    """换到新数据目录时，把上次的存档路径带过去（只复制，不动原文件）。"""
    target = Path(data_dir) / "world.json"
    if target.is_file():
        return
    try:
        if LEGACY_WORLD_FILE.is_file() and LEGACY_WORLD_FILE != target:
            shutil.copy2(LEGACY_WORLD_FILE, target)
    except OSError:
        pass


def choose_data_dir_dialog():
    """首次运行询问数据放在哪里，返回 (目录, 模式)；用户放弃则返回 (None, None)。"""
    import tkinter as tk

    portable = portable_dir()
    roaming = appdata_dir()
    result = {}

    root = tk.Tk()
    root.title(f"{APP_TITLE} · 首次启动")
    root.resizable(False, False)
    root.attributes("-topmost", True)

    tk.Label(
        root,
        text="选择数据存放位置",
        font=("Microsoft YaHei UI", 13, "bold"),
    ).pack(padx=24, pady=(20, 6))
    tk.Label(
        root,
        justify="left",
        wraplength=430,
        text=(
            "这里保存地图瓦片缓存、上次的存档记录和备份配置。\n"
            "两种选择都可以随时删除该目录后重新选择。"
        ),
    ).pack(padx=24, pady=(0, 12))

    def make_line(parent, title, path):
        box = tk.Frame(parent)
        box.pack(fill="x", padx=24)
        tk.Label(box, text=title, anchor="w", font=("Microsoft YaHei UI", 9, "bold")).pack(fill="x")
        tk.Label(box, text=str(path), anchor="w", wraplength=430, fg="#666").pack(fill="x")

    make_line(root, "便携：与程序放在同一目录", portable)
    make_line(root, "系统目录：重装程序也不会丢", roaming)

    def finish(value):
        result["value"] = value
        root.destroy()

    buttons = tk.Frame(root)
    buttons.pack(pady=18)
    tk.Button(buttons, text="便携", width=12, command=lambda: finish(("portable", portable))).pack(side="left", padx=6)
    tk.Button(buttons, text="系统目录", width=12, command=lambda: finish(("appdata", roaming))).pack(side="left", padx=6)
    tk.Button(buttons, text="退出", width=12, command=lambda: finish(None)).pack(side="left", padx=6)
    root.protocol("WM_DELETE_WINDOW", lambda: finish(None))
    root.mainloop()

    if not result.get("value"):
        return None, None
    mode, path = result["value"]
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
    except OSError as e:
        show_error(f"无法创建数据目录：{e}\n已改用系统目录")
        mode, path = "appdata", roaming
        path.mkdir(parents=True, exist_ok=True)
    return path, mode


def show_error(message):
    """打包成无控制台的 exe 后，print 是看不见的，用消息框兜底。"""
    print(message)
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        messagebox.showerror(APP_TITLE, message)
        root.destroy()
    except Exception:
        pass


def resolve_data_dir(args):
    if args.data_dir:
        path = Path(args.data_dir).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path, "custom"
    if not args.choose:
        for mode, path in (("portable", portable_dir()), ("appdata", appdata_dir())):
            if has_marker(path):
                return path, mode
    path, mode = choose_data_dir_dialog()
    if path is not None:
        write_marker(path, mode)
    return path, mode


def parse_args(argv):
    import argparse

    parser = argparse.ArgumentParser(description=f"{APP_TITLE} · 桌面版")
    parser.add_argument("--world", help="启动时直接加载的存档目录")
    parser.add_argument("--port", type=int, default=None, help="指定端口，占用则报错退出")
    parser.add_argument("--data-dir", help="直接使用指定数据目录（不弹首次选择）")
    parser.add_argument("--choose", action="store_true", help="重新选择数据存放位置")
    parser.add_argument("--verbose", action="store_true", help="打开调试输出")
    return parser.parse_args(argv)


def run_backup_child(argv):
    """--run-backup 子命令：exe 自己当备份子进程（打包后没有独立的 python）。"""
    for name, fd in (("stdout", 1), ("stderr", 2)):
        if getattr(sys, name, None) is None:
            try:
                setattr(sys, name, open(fd, "w", encoding="utf-8", errors="replace", closefd=False))
            except OSError:
                setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))
    import backup_runner

    sys.argv = ["backup_runner.py"] + argv
    return backup_runner.main()


def make_closing_handler(window):
    def on_closing():
        if not server.backup_running():
            return None
        keep = window.create_confirmation_dialog(
            "备份还没有结束",
            "现在退出会中断本次备份。确定要退出吗？",
        )
        return None if keep else False

    return on_closing


def run_desktop(args):
    data_dir, mode = resolve_data_dir(args)
    if data_dir is None:
        return 0

    server.VERBOSE = args.verbose
    configs_dir = None if FROZEN else PROJECT_DIR / "configs"
    server.configure_storage(data_dir, configs_dir=configs_dir)
    seed_world_file(data_dir)

    try:
        import webview
    except ImportError:
        show_error(
            "缺少 pywebview，无法打开桌面窗口。\n"
            "源码运行时请先执行：pip install pywebview\n"
            "或直接使用打包好的 exe。"
        )
        return 1

    if args.world:
        try:
            server.load_world(args.world, persist=True)
        except ValueError as e:
            show_error(f"无法加载存档：{e}")

    server.start_executor()
    try:
        httpd, port = server.create_server(args.port)
    except RuntimeError as e:
        show_error(str(e))
        server.stop_server(None)
        return 1
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    window = webview.create_window(
        APP_TITLE,
        url=f"http://127.0.0.1:{port}/",
        width=1600,
        height=900,
        min_size=(980, 620),
        text_select=True,
        background_color="#080b10",
    )
    window.events.closing += make_closing_handler(window)
    print(f"{APP_TITLE} · 数据目录（{mode}）：{data_dir}")
    try:
        webview.start(
            gui="edgechromium",
            debug=args.verbose,
            private_mode=False,
            storage_path=str(Path(data_dir) / "webview"),
        )
    finally:
        try:
            server.stop_server(httpd)
        except Exception as e:
            print(f"停止后端时出错：{e}")
    # 窗口已关闭、后端已停：直接结束进程。
    # 打包后的解释器收尾会等待进程池，容易留下不退出的驻留进程。
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.flush()
        except Exception:
            pass
    os._exit(0)


def main():
    argv = sys.argv[1:]
    if argv and argv[0] == "--run-backup":
        return run_backup_child(argv[1:])
    multiprocessing.freeze_support()
    try:
        return run_desktop(parse_args(argv))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
