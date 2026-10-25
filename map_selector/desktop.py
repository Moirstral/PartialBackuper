"""MC存档选区备份工具 · 桌面版入口。

双击 exe（或 python desktop.py）即：复用/选择数据目录 → 起本地后端 → 开内嵌 WebView2 无边框窗口。
窗口按钮、托盘、关闭询问、数据目录选择、拖入存档都通过 /api/desktop/* 与页面通信。
关闭窗口时后端随进程一起退出，不再有浏览器、PWA 与协议拉起。
"""
import ctypes
import hashlib
import json
import multiprocessing
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import urllib.request
from ctypes import wintypes
from pathlib import Path
from urllib.parse import unquote

APP_TITLE = "MC存档选区备份工具"
PORTABLE_DIR_NAME = "UserData"
APPDATA_DIR_NAME = "PartialBackuper"
PENDING_DIR_NAME = "PartialBackuper-setup"
PROFILE_DIR_NAME = "webview"
MARKER_NAME = "storage.json"
SETTINGS_NAME = "settings.json"
LOCK_NAME = "desktop.lock.json"
WINDOW_NAME = "window.json"
DEFAULT_WINDOW_SIZE = (1600, 900)
MIN_WINDOW_SIZE = (980, 620)

# 点关闭（窗口按钮或 Alt+F4）时的行为：每次询问 / 收进托盘 / 直接退出
ON_CLOSE_SETTING = "on_close"
CLOSE_ASK = "ask"
CLOSE_TRAY = "tray"
CLOSE_EXIT = "exit"
CLOSE_CHOICES = (CLOSE_ASK, CLOSE_TRAY, CLOSE_EXIT)

SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020
MONITOR_DEFAULTTONULL = 0x00000000
MONITOR_DEFAULTTONEAREST = 0x00000002
SPI_GETWORKAREA = 0x0030
SM_CXSIZEFRAME = 32
SM_CXPADDEDBORDER = 33
SM_CXDRAG = 68
SM_CYDRAG = 69
SM_CXDOUBLECLK = 36
SM_CYDOUBLECLK = 37
# 无边框窗口要自己补上的样式位与消息：少了 WS_MINIMIZEBOX，点任务栏按钮不会最小化
GWL_STYLE = -16
GWL_WNDPROC = -4
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WM_GETMINMAXINFO = 0x0024
WM_NCCALCSIZE = 0x0083
WM_ENTERSIZEMOVE = 0x0231
WM_EXITSIZEMOVE = 0x0232
WM_NCLBUTTONDOWN = 0x00A1
VK_LBUTTON = 0x01
HTCAPTION = 2
HTTOP = 12
HTBOTTOM = 15
HTLEFT = 10
HTRIGHT = 11
HTTOPLEFT = 13
HTTOPRIGHT = 14
HTBOTTOMLEFT = 16
HTBOTTOMRIGHT = 17
# 页面按下哪儿 → 报给系统哪个「非客户区」代码：之后拖动、拉伸、双击放大还原、贴边分屏
# 全由系统的模态循环负责（含光标形状、动画、还原回原位），我们一行窗口算术都不写。
HT_TARGETS = {
    "caption": HTCAPTION,
    "top": HTTOP,
    "bottom": HTBOTTOM,
    "left": HTLEFT,
    "right": HTRIGHT,
    "top-left": HTTOPLEFT,
    "top-right": HTTOPRIGHT,
    "bottom-left": HTBOTTOMLEFT,
    "bottom-right": HTBOTTOMRIGHT,
}
SW_MAXIMIZE = 3
SW_RESTORE = 9

FROZEN = getattr(sys, "frozen", False)
BASE_DIR = Path(__file__).resolve().parent
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", BASE_DIR)) if FROZEN else BASE_DIR
PROJECT_DIR = RESOURCE_DIR if FROZEN else BASE_DIR.parent
PROGRAM_DIR = Path(sys.executable).resolve().parent if FROZEN else PROJECT_DIR
LEGACY_WORLD_FILE = BASE_DIR / "world.json"
ICON_FILE = RESOURCE_DIR / "app.ico"

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


def pending_dir():
    path = Path(tempfile.gettempdir()) / PENDING_DIR_NAME
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        return appdata_dir()
    return path


def marker_path(root):
    return Path(root) / MARKER_NAME


def has_marker(root):
    try:
        return marker_path(root).is_file()
    except OSError:
        return False


def read_marker(root):
    try:
        data = json.loads(marker_path(root).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def writable_dir(path):
    """真写一个探测文件：只读目录、被别的程序占住的目录都算不可用。"""
    probe = Path(path) / f".write-probe-{os.getpid()}"
    try:
        probe.write_text("ok", encoding="utf-8")
    except OSError:
        return False
    try:
        probe.unlink()
    except OSError:
        pass
    return True


def usable_marker(root, mode):
    """目录里的标记是不是本程序留下的、属于这个模式，而且目录还能写。"""
    marker = read_marker(root)
    return (
        marker.get("app") == APP_TITLE
        and marker.get("mode") == mode
        and Path(root).is_dir()
        and writable_dir(root)
    )


def write_marker(root, mode):
    try:
        marker_path(root).write_text(
            json.dumps({"app": APP_TITLE, "mode": mode}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as e:
        print(f"数据目录标记写入失败：{e}")


def clear_markers(keep):
    """换过存放位置后，旧目录里的标记要清掉，否则下次启动会找回旧位置。"""
    keep = Path(keep).resolve()
    for path in (portable_dir(), appdata_dir()):
        try:
            if has_marker(path) and path.resolve() != keep:
                marker_path(path).unlink()
        except OSError:
            pass


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


def migrate_profile(src, dst):
    """换数据目录后把 WebView2 的配置（含未保存的配置）搬到新位置。"""
    src, dst = Path(src), Path(dst)
    if not src.is_dir() or src.resolve() == dst.resolve():
        return
    for _ in range(10):
        try:
            shutil.copytree(str(src), str(dst), dirs_exist_ok=True)
            return
        except OSError:
            time.sleep(0.3)  # 上一个实例的 WebView2 子进程可能还没松手


def carry_user_files(src, dst):
    """换数据目录时把窗口设置和存档记录带过去，新目录里已有的不覆盖。"""
    src, dst = Path(src), Path(dst)
    for name in (SETTINGS_NAME, WINDOW_NAME, "world.json"):
        source, target = src / name, dst / name
        try:
            if source.is_file() and not target.exists():
                target.write_bytes(source.read_bytes())
        except OSError:
            pass


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
    """返回 (数据目录, 模式, 是否需要弹窗选择)。"""
    if args.data_dir:
        path = Path(args.data_dir).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        # 重启时会显式带上 --data-dir，模式仍按目录里的标记显示
        mode = read_marker(path).get("mode") or "custom"
        return path, mode, False
    if not args.choose:
        # 便携优先：exe 同目录的 UserData 只要标记对得上、还能写，就直接沿用，不再问用户。
        # 没有可用的 UserData 时，沿用上次选的系统目录（否则每次启动都要重选一遍）。
        for mode, path in (("portable", portable_dir()), ("appdata", appdata_dir())):
            if usable_marker(path, mode):
                return path, mode, False
    return pending_dir(), "pending", True


def parse_args(argv):
    import argparse

    parser = argparse.ArgumentParser(description=f"{APP_TITLE} · 桌面版")
    parser.add_argument("--world", help="启动时直接加载的存档目录")
    parser.add_argument("--port", type=int, default=None, help="指定端口，占用则报错退出")
    parser.add_argument("--data-dir", help="直接使用指定数据目录（不弹首次选择）")
    parser.add_argument("--choose", action="store_true", help="在窗口里重新选择数据存放位置")
    parser.add_argument("--import-profile", help=argparse.SUPPRESS)
    parser.add_argument("--takeover", action="store_true", help=argparse.SUPPRESS)
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


# ------------------------------------------------------------------ 窗口几何

class MonitorInfo(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
    ]


class MinMaxInfo(ctypes.Structure):
    _fields_ = [
        ("ptReserved", wintypes.POINT),
        ("ptMaxSize", wintypes.POINT),
        ("ptMaxPosition", wintypes.POINT),
        ("ptMinTrackSize", wintypes.POINT),
        ("ptMaxTrackSize", wintypes.POINT),
    ]


class WindowPlacement(ctypes.Structure):
    _fields_ = [
        ("length", wintypes.UINT),
        ("flags", wintypes.UINT),
        ("showCmd", wintypes.UINT),
        ("ptMinPosition", wintypes.POINT),
        ("ptMaxPosition", wintypes.POINT),
        ("rcNormalPosition", wintypes.RECT),
    ]


def monitor_rects(hwnd):
    """当前显示器的 (全屏矩形, 去掉任务栏的工作区矩形)，都是屏幕绝对坐标。"""
    info = MonitorInfo()
    info.cbSize = ctypes.sizeof(MonitorInfo)
    monitor = ctypes.windll.user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
    if not monitor or not ctypes.windll.user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
        return None
    full, work = info.rcMonitor, info.rcWork
    return (full.left, full.top, full.right, full.bottom), (work.left, work.top, work.right, work.bottom)


def monitor_work(hwnd):
    """当前显示器去掉任务栏后的范围：(相对显示器的左上角偏移, 宽, 高)。"""
    rects = monitor_rects(hwnd)
    if not rects:
        return None
    full, work = rects
    return (work[0] - full[0], work[1] - full[1], work[2] - work[0], work[3] - work[1])


# 无边框窗口的最大化/还原只有让系统自己切状态才有 Win11 动画，
# 所以挂钩 WM_GETMINMAXINFO 把「最大化」改成贴工作区，否则会盖住任务栏。
# 回调和原过程都要一直留着引用：被 GC 掉之后窗口收到消息就直接崩了。
_window_procs = {}
# 系统的拖动/缩放模态循环进出了多少次、此刻在不在里面：
# 页面转告的那一按到底有没有被系统接手，看这个就知道（接口原样回报，测试也照它断言）。
_size_move = {"entered": 0, "inside": False}

def cursor_pos():
    """当前鼠标的屏幕坐标：交给系统的按下消息要用它当拖动/缩放的起点。"""
    user32 = ctypes.windll.user32
    point = wintypes.POINT()
    if not user32.GetCursorPos(ctypes.byref(point)):
        return (0, 0)
    return (point.x, point.y)


def is_ui_thread(hwnd):
    """这一按是不是在窗口自己那条线程上发出的：系统的拖动循环只认自己线程的请求。"""
    user32 = ctypes.windll.user32
    pid = wintypes.DWORD()
    owner = user32.GetWindowThreadProcessId(ctypes.c_void_p(hwnd), ctypes.byref(pid))
    return owner == ctypes.windll.kernel32.GetCurrentThreadId()


def button_down():
    """左键此刻是不是真按着：系统的拖动/缩放循环只在这种情况下才接得住这一按。"""
    return bool(ctypes.windll.user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000)


def resize_band(hwnd):
    """系统留给「拉伸手」的厚度（物理像素）：页面照这个宽度判断按下去算不算贴边。"""
    user32 = ctypes.windll.user32
    try:
        dpi = user32.GetDpiForWindow(ctypes.c_void_p(hwnd)) or 96
        frame = user32.GetSystemMetricsForDpi(SM_CXSIZEFRAME, dpi)
        pad = user32.GetSystemMetricsForDpi(SM_CXPADDEDBORDER, dpi)
        band = frame + pad
        return band if band > 0 else 8
    except Exception as e:
        print(f"读取系统边框厚度失败：{e}")
        return 8


def drag_threshold(hwnd):
    """系统认定的「这一下算拖动」的位移（物理像素）：按下不动是单击，越过它才是拖动。
    普通标题栏是 DefWindowProc 自己按这个数等着的，这里由页面等，因为按下根本到不了窗口过程。"""
    user32 = ctypes.windll.user32
    try:
        dpi = user32.GetDpiForWindow(ctypes.c_void_p(hwnd)) or 96
        width = user32.GetSystemMetricsForDpi(SM_CXDRAG, dpi)
        height = user32.GetSystemMetricsForDpi(SM_CYDRAG, dpi)
        return max(width, height) if width > 0 and height > 0 else 4
    except Exception as e:
        print(f"读取系统拖动阈值失败：{e}")
        return 4


def second_click(hwnd, prev, point, now):
    """这一按算不算上一按的双击：判据全用系统给的数（双击间隔 + 双击范围），
    和普通标题栏一样。连击数不能问浏览器——第一按只要挪过了拖动阈值就交给系统了，
    系统的模态循环会把松开吃掉，浏览器从此认定左键还按着，第二下就再也数不出来，双击放大直接没了。"""
    user32 = ctypes.windll.user32
    try:
        dpi = user32.GetDpiForWindow(ctypes.c_void_p(hwnd)) or 96
        span = user32.GetDoubleClickTime() or 500
        width = user32.GetSystemMetricsForDpi(SM_CXDOUBLECLK, dpi) or 4
        height = user32.GetSystemMetricsForDpi(SM_CYDOUBLECLK, dpi) or 4
    except Exception as e:
        print(f"读取系统双击判据失败：{e}")
        span, width, height = 500, 4, 4
    if (now - prev["at"]) * 1000 > span:
        return False
    dx = abs(point[0] - prev["point"][0])
    dy = abs(point[1] - prev["point"][1])
    return dx <= width and dy <= height


class NCCalcSizeParams(ctypes.Union):
    """WM_NCCALCSIZE 的参数：uMsg 和 rgrc[3] 是同一块内存，所以得用 union。"""

    _fields_ = [("uMsg", wintypes.DWORD), ("rgrc", wintypes.RECT * 3)]


def install_window_hooks(hwnd):
    """补上系统窗口的样式位并挂钩窗口过程：动画、圆角、任务栏切换全靠这些样式。

    样式位有了标题栏和缩放边框，但 WM_NCCALCSIZE 把非客户区压成零，画面上仍然是无边框。
    """
    user32 = ctypes.windll.user32
    if hwnd in _window_procs:
        return True
    if ctypes.sizeof(ctypes.c_void_p) > 4:
        get_ptr, set_ptr = user32.GetWindowLongPtrW, user32.SetWindowLongPtrW
    else:  # 32 位没有 PtrW 导出，只能退回旧名字
        get_ptr, set_ptr = user32.GetWindowLongW, user32.SetWindowLongW
    get_ptr.restype = ctypes.c_void_p
    get_ptr.argtypes = [ctypes.c_void_p, ctypes.c_int]
    set_ptr.restype = ctypes.c_void_p
    set_ptr.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
    proc_type = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_void_p, ctypes.c_uint,
                                   ctypes.c_void_p, ctypes.c_ssize_t)

    def wnd_proc(target, msg, wparam, lparam):
        if msg == WM_NCCALCSIZE and wparam:
            params = NCCalcSizeParams.from_address(lparam)
            outer = (params.rgrc[0].left, params.rgrc[0].top,
                     params.rgrc[0].right, params.rgrc[0].bottom)
            old_proc(target, msg, wparam, lparam)
            if is_maximized(target):
                # 系统最大化会把窗口向外多推一圈边框，客户区直接钉成工作区才不会压到任务栏
                rects = monitor_rects(target)
                if rects:
                    work = rects[1]
                    params.rgrc[0].left, params.rgrc[0].top = work[0], work[1]
                    params.rgrc[0].right, params.rgrc[0].bottom = work[2], work[3]
                    return 0
            # 系统算出来的是「扣掉标题栏和边框」的客户区，改回整个窗口：边框不画，只留样式
            params.rgrc[0].left, params.rgrc[0].top = outer[0], outer[1]
            params.rgrc[0].right, params.rgrc[0].bottom = outer[2], outer[3]
            return 0
        if msg == WM_ENTERSIZEMOVE:
            _size_move["entered"] += 1
            _size_move["inside"] = True
        elif msg == WM_EXITSIZEMOVE:
            _size_move["inside"] = False
        result = old_proc(target, msg, wparam, lparam)
        if msg == WM_GETMINMAXINFO:
            try:
                area = monitor_work(target)
                if area:
                    info = MinMaxInfo.from_address(lparam)
                    info.ptMaxPosition.x, info.ptMaxPosition.y = area[0], area[1]
                    info.ptMaxSize.x, info.ptMaxSize.y = area[2], area[3]
            except Exception as e:
                print(f"最大化范围设置失败：{e}")
        return result

    callback = proc_type(wnd_proc)
    old_address = set_ptr(ctypes.c_void_p(hwnd), GWL_WNDPROC,
                          ctypes.cast(callback, ctypes.c_void_p))
    if not old_address:
        print("窗口过程挂钩失败，最大化会退回自己算范围")
        return False
    old_proc = proc_type(old_address)
    _window_procs[hwnd] = (callback, old_proc)

    style = user32.GetWindowLongW(ctypes.c_void_p(hwnd), GWL_STYLE)
    user32.SetWindowLongW(
        ctypes.c_void_p(hwnd), GWL_STYLE,
        style | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_CAPTION | WS_THICKFRAME,
    )
    # 样式改了要重算一次非客户区，挂钩才来得及把它压回去
    user32.SetWindowPos(ctypes.c_void_p(hwnd), 0, 0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED)
    return True


def is_maximized(hwnd):
    return bool(ctypes.windll.user32.IsZoomed(ctypes.c_void_p(hwnd)))


# ------------------------------------------------------------------ 窗口几何记忆
# 窗口接口收的是逻辑像素，系统给的矩形是物理像素：存的时候除、开的时候乘，
# 高缩放屏上才不会每启动一次就缩一点。是否声明 DPI 感知由这里兜底（pywebview 启动时也会声明一次）。

_dpi_aware = False


def dpi_scale(hwnd=0):
    """逻辑像素 → 物理像素的倍数。"""
    global _dpi_aware
    user32 = ctypes.windll.user32
    if not _dpi_aware:
        _dpi_aware = True
        try:
            user32.SetProcessDPIAware()
        except Exception as e:
            print(f"声明 DPI 感知失败：{e}")
    try:
        dpi = user32.GetDpiForWindow(ctypes.c_void_p(hwnd)) if hwnd else user32.GetDpiForSystem()
    except Exception:
        dpi = 96
    return (dpi or 96) / 96.0


def primary_work():
    """主显示器去掉任务栏后的范围（物理像素）。"""
    rect = wintypes.RECT()
    if ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0):
        return (rect.left, rect.top, rect.right, rect.bottom)
    return None


def work_area(left, top, width, height):
    """这块矩形落在哪台显示器上，返回那台的可用范围；完全不在任何屏幕上就是 None。"""
    rect = wintypes.RECT(left, top, left + width, top + height)
    user32 = ctypes.windll.user32
    monitor = user32.MonitorFromRect(ctypes.byref(rect), MONITOR_DEFAULTTONULL)
    if not monitor:
        return None
    info = MonitorInfo()
    info.cbSize = ctypes.sizeof(MonitorInfo)
    if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
        return None
    work = info.rcWork
    return (work.left, work.top, work.right, work.bottom)


def window_rect(hwnd):
    """窗口现在的屏幕矩形 (x, y, 宽, 高)，物理像素。
    最大化或最小化时取系统记着的「还原后」矩形，下次打开就回到放大之前的位置和大小。"""
    user32 = ctypes.windll.user32
    if is_maximized(hwnd) or user32.IsIconic(ctypes.c_void_p(hwnd)):
        placement = WindowPlacement()
        placement.length = ctypes.sizeof(WindowPlacement)
        if user32.GetWindowPlacement(ctypes.c_void_p(hwnd), ctypes.byref(placement)):
            rect = placement.rcNormalPosition
            return (rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)
    rect = wintypes.RECT()
    if user32.GetWindowRect(ctypes.c_void_p(hwnd), ctypes.byref(rect)):
        return (rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)
    return None


def window_file(data_dir):
    return Path(data_dir) / WINDOW_NAME


def load_window_rect(data_dir):
    """上次关窗时的矩形（逻辑像素）；没有记录或写坏了都当没记过。"""
    try:
        data = json.loads(window_file(data_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    values = [data.get(key) for key in ("x", "y", "width", "height")]
    if not all(isinstance(value, int) and not isinstance(value, bool) for value in values):
        return None
    return tuple(values)


def save_window_rect(data_dir, hwnd):
    """把窗口矩形记进数据目录（逻辑像素）。最大化时记的是还原后的矩形。"""
    rect = window_rect(hwnd)
    if not rect:
        return False
    scale = dpi_scale(hwnd)
    x, y, width, height = [int(round(value / scale)) for value in rect]
    if width < MIN_WINDOW_SIZE[0] or height < MIN_WINDOW_SIZE[1]:
        return False
    try:
        window_file(data_dir).write_text(
            json.dumps({"x": x, "y": y, "width": width, "height": height}), encoding="utf-8")
        return True
    except OSError as e:
        print(f"记录窗口大小失败：{e}")
        return False


def logical_rect(rect, scale):
    return {
        "x": int(round(rect[0] / scale)),
        "y": int(round(rect[1] / scale)),
        "width": int(round(rect[2] / scale)),
        "height": int(round(rect[3] / scale)),
    }


def physical_rect(rect):
    """逻辑矩形 → 物理矩形：开窗后按它把窗口摆正。"""
    scale = dpi_scale()
    return tuple(int(round(rect[key] * scale)) for key in ("x", "y", "width", "height"))


def fit_window_rect(x, y, width, height):
    """把记下的矩形夹在它所在显示器的可用范围里；完全不在任何屏幕上就返回 None。"""
    if width < MIN_WINDOW_SIZE[0] or height < MIN_WINDOW_SIZE[1]:
        return None
    scale = dpi_scale()
    left, top = int(round(x * scale)), int(round(y * scale))
    wide, tall = int(round(width * scale)), int(round(height * scale))
    work = work_area(left, top, wide, tall)
    if work is None:
        return None
    work_w, work_h = work[2] - work[0], work[3] - work[1]
    wide, tall = min(wide, work_w), min(tall, work_h)
    left = min(max(left, work[0]), work[2] - wide)
    top = min(max(top, work[1]), work[3] - tall)
    return logical_rect((left, top, wide, tall), scale)


def centered_rect():
    """默认大小放在主显示器工作区正中；屏幕太小时缩到放得下。"""
    scale = dpi_scale()
    work = primary_work() or (0, 0, DEFAULT_WINDOW_SIZE[0], DEFAULT_WINDOW_SIZE[1])
    work_w, work_h = work[2] - work[0], work[3] - work[1]
    wide = min(int(round(DEFAULT_WINDOW_SIZE[0] * scale)), work_w)
    tall = min(int(round(DEFAULT_WINDOW_SIZE[1] * scale)), work_h)
    left = work[0] + (work_w - wide) // 2
    top = work[1] + (work_h - tall) // 2
    return logical_rect((left, top, wide, tall), scale)


def startup_rect(data_dir):
    """开窗矩形（逻辑像素）：优先上次记下的；没有记录、或记录已经放不进任何显示器，
    就按默认大小居中。"""
    saved = load_window_rect(data_dir)
    if saved:
        fitted = fit_window_rect(*saved)
        if fitted:
            return fitted
    return centered_rect()


# ------------------------------------------------------------------ 任务栏文字

def set_native_title(uid, text):
    """无边框没有标题栏，但任务栏预览与 Alt+Tab 仍显示这段文字。"""
    from webview.platforms.winforms import set_title

    set_title(text, uid)




# ------------------------------------------------------------------ 托盘

class TrayIcon:
    """系统托盘图标：独立 STA 线程跑 WinForms 消息循环（pythonnet）。

    左键单击切换显示/隐藏，右键菜单同义；图标挂上后留到进程结束，免得窗口反而找不见。
    """

    def __init__(self, icon_path, tooltip, on_toggle, on_quit):
        self.icon_path = str(icon_path)
        self.tooltip = tooltip
        self.on_toggle = on_toggle
        self.on_quit = on_quit
        self._thread = None
        self._notify = None
        self._context = None
        self._broken = False
        self._last_click = 0.0

    def start(self):
        """起托盘线程并等图标建出来，返回是否可用。"""
        if self._thread is None:
            try:
                import clr  # noqa: F401  必须先导入才有 System 命名空间
                from System.Threading import ApartmentState, ThreadStart
                from System.Threading import Thread as NetThread
            except Exception as e:
                print(f"托盘不可用：{e}")
                self._broken = True
                return False
            thread = NetThread(ThreadStart(self._loop))
            thread.SetApartmentState(ApartmentState.STA)
            thread.IsBackground = True
            self._thread = thread
            thread.Start()
            for _ in range(40):
                if self._notify is not None or self._broken:
                    break
                time.sleep(0.05)  # 托盘线程是异步起循环的
        return self._notify is not None

    def _loop(self):
        from System import EventHandler
        from System.Drawing import Icon
        from System.Windows.Forms import (
            ApplicationContext,
            Application,
            ContextMenuStrip,
            MouseEventHandler,
            NotifyIcon,
            ToolStripMenuItem,
        )

        notify = NotifyIcon()
        try:
            # 按托盘的实际像素取帧：默认的 Icon(path) 会挑 32 帧再让系统缩到 16，小图会糊成一团
            from System.Windows.Forms import SystemInformation

            small = SystemInformation.SmallIconSize.Width
            notify.Icon = Icon(self.icon_path, small, small)
        except Exception:
            try:
                notify.Icon = Icon(self.icon_path)
            except Exception as e:
                print(f"托盘图标加载失败：{e}")
                self._broken = True
                return
        notify.Text = self.tooltip

        menu = ContextMenuStrip()
        item_show = ToolStripMenuItem("显示 / 隐藏主窗口")
        item_show.add_Click(EventHandler(self._activate))
        item_quit = ToolStripMenuItem("退出")
        item_quit.add_Click(EventHandler(self._handle_quit))
        menu.Items.Add(item_show)
        menu.Items.Add(item_quit)
        notify.ContextMenuStrip = menu
        # 左键抬起即切换显示/隐藏；真实点击有时只给 Click，所以两个都接，用防抖合并成一次
        notify.add_MouseUp(MouseEventHandler(self._handle_mouse))
        notify.add_Click(EventHandler(self._activate))

        try:
            # 图标必须由跑消息循环的这个线程挂载：窗口挂在哪个线程，点击消息就发到哪个线程，
            # 在别的线程挂会做成「图标看得见、点了没反应」
            notify.Visible = True
        except Exception as e:
            print(f"托盘图标挂载失败：{e}")
            self._broken = True
            notify.Dispose()
            return
        self._notify = notify
        context = ApplicationContext()
        self._context = context
        try:
            Application.Run(context)
        finally:
            notify.Visible = False
            notify.Dispose()
            self._notify = None

    def _handle_mouse(self, sender, args):
        from System.Windows.Forms import MouseButtons

        if args.Button != MouseButtons.Left:
            return  # 右键弹菜单，中键不管
        self._click_toggle()

    def _activate(self, sender, args):
        self._click_toggle()

    def _click_toggle(self):
        """一次抬起会连着派发 MouseUp 和 Click（同一条消息，间隔为零），
        托盘上顺手双击也很常见：0.45 秒内的重复点击算一次切换，免得唤回后又被第二下收回去。"""
        now = time.monotonic()
        if now - self._last_click < 0.45:
            return
        self._last_click = now
        self._run(self.on_toggle, "切换主窗口失败")

    def _handle_quit(self, sender, args):
        self._run(self.on_quit, "退出失败")

    def _run(self, callback, message):
        """托盘回调必须自己吃掉异常：异常会打断托盘线程，图标和窗口会一起消失。"""
        try:
            callback()
        except Exception as e:
            print(f"{message}：{e}")
            traceback.print_exc()

    def stop(self):
        """只发退出信号：摘图标和释放都由托盘线程自己做，跨线程碰 NotifyIcon 会踩到消息窗口所属线程。"""
        context, self._context = self._context, None
        try:
            if context is not None:
                context.ExitThread()
        except Exception as e:
            print(f"托盘退出失败：{e}")


# ------------------------------------------------------------------ 桌面桥

class DesktopBridge:
    """页面通过 /api/desktop/* 调用的窗口按钮、托盘、关闭询问、数据目录与拖入存档逻辑。"""

    def __init__(self, args, data_dir, mode, setup_required):
        self.args = args
        self.data_dir = Path(data_dir)
        self.mode = mode
        self.setup_required = setup_required
        self.window = None
        self.httpd = None
        self.tray = None
        self.pending_world = ""
        self.settings = self._load_settings()
        self._drop_registered = False
        self._hooks_installed = False
        self._state_watched = False
        self._loop_running = False
        self._last_press = None
        self._armed_press = None
        self._last_down = None
        self._dblclk_press = False
        self._press_log = []
        self._allow_close = False
        self.start_rect = None  # 开窗时算好的物理矩形，页面一显示就按它摆正
        self._rect_applied = False

    # ---- 设置文件

    @property
    def settings_path(self):
        return self.data_dir / SETTINGS_NAME

    def _load_settings(self):
        merged = {ON_CLOSE_SETTING: CLOSE_ASK}
        try:
            saved = json.loads(self.settings_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            saved = {}
        if isinstance(saved, dict) and saved.get(ON_CLOSE_SETTING) in CLOSE_CHOICES:
            merged[ON_CLOSE_SETTING] = saved[ON_CLOSE_SETTING]
        return merged

    def _save_settings(self):
        try:
            self.settings_path.write_text(
                json.dumps(self.settings, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except OSError as e:
            print(f"窗口设置写入失败：{e}")

    # ---- 状态

    def api_state(self, payload=None):
        world = server.get_world()
        hwnd = self.hwnd()
        return {
            "enabled": True,
            "setup": self.setup_required,
            "mode": self.mode,
            "dataDir": str(self.data_dir),
            "world": world.info["path"] if world else "",
            "options": {"portable": str(portable_dir()), "appdata": str(appdata_dir())},
            "settings": dict(self.settings),
            "maximized": self.maximized,
            "trayAvailable": ICON_FILE.is_file(),
            "resizeBand": resize_band(hwnd) if hwnd else 8,
            "dragThreshold": drag_threshold(hwnd) if hwnd else 4,
            # 上一次「页面转告的按下」到底走到哪一步：拖动要真按住左键才测得出来，出问题时看这里
            "lastPress": dict(self._last_press or {}),
            # 最近几按的流水（谁按的、哪一步、判成了什么）：真机上的双击问题只能照它复盘
            "pressLog": list(self._press_log),
        }

    def attach(self, window, httpd):
        self.window = window
        self.httpd = httpd

    def hwnd(self):
        if self.window is None:
            return 0
        try:
            from webview.platforms.winforms import BrowserView

            instance = BrowserView.instances.get(self.window.uid)
            return instance.Handle.ToInt32() if instance else 0
        except Exception as e:
            print(f"取窗口句柄失败：{e}")
            return 0

    @property
    def maximized(self):
        """最大化状态问系统要：切换都走 ShowWindow，自己记的标记会和工作区实际状态对不上。"""
        hwnd = self.hwnd()
        return bool(hwnd) and is_maximized(hwnd)

    def install_native_window(self):
        """页面加载完再动窗口样式：这时才有原生句柄可挂钩。"""
        if self._hooks_installed:
            return
        hwnd = self.hwnd()
        if not hwnd:
            return
        self._hooks_installed = install_window_hooks(hwnd)
        self.watch_window_state()

    def apply_start_rect(self, *args):
        """窗口一显示就按算好的物理矩形摆正。

        无边框窗口是被「先按有边框创建、再去掉边框」做出来的，去掉那一刻 WinForms 会把
        整个窗口连带缩掉一圈（100% 缩放下正好窄 16、矮 39）。与其去猜边框厚度，不如等
        句柄有了直接摆回要的位置：逻辑和记录都只存真正的窗口矩形。"""
        if self._rect_applied or not self.start_rect:
            return
        hwnd = self.hwnd()
        if not hwnd:
            return
        self._rect_applied = True
        user32 = ctypes.windll.user32
        if _size_move["entered"] or is_maximized(hwnd) or user32.IsIconic(ctypes.c_void_p(hwnd)):
            return  # 这一会儿用户已经自己动过窗口了，别抢
        x, y, width, height = self.start_rect
        user32.SetWindowPos(ctypes.c_void_p(hwnd), 0, x, y, width, height,
                            SWP_NOZORDER | SWP_NOACTIVATE)

    def watch_window_state(self):
        """窗口状态由系统改（双击顶栏、Win+↑、任务栏、贴边分屏），页面得跟着知道，
        不然右上角那个图标会停在旧样子。轮询一下推给页面，比在各处切换后补一句可靠。"""
        if self._state_watched:
            return
        self._state_watched = True

        def loop():
            last = None
            while True:
                try:
                    hwnd = self.hwnd()
                    zoomed = bool(hwnd) and is_maximized(hwnd)
                    if zoomed != last:
                        last = zoomed
                        self.push("DesktopWindowState", {"maximized": zoomed})
                except Exception as e:
                    print(f"窗口状态同步失败：{e}")
                time.sleep(0.25)

        threading.Thread(target=loop, daemon=True).start()

    # ---- 窗口按钮
    # 右上角那三个按钮照常代劳；拖动、贴边拉伸走系统的模态循环，双击放大还原走 ShowWindow（见 api_press）。

    def api_window(self, payload):
        action = (payload or {}).get("action")
        if action == "minimize":
            self.window.minimize()
        elif action == "toggle-maximize":
            self.toggle_maximize()
        elif action == "close":
            self.window.destroy()  # 走 closing 事件：询问、收托盘都在那里决定
        else:
            raise ValueError("未知的窗口动作")
        return {"maximized": self.maximized}

    def api_press(self, payload):
        """页面把「按住了标题栏/某条边」转告过来，接下来全是系统的事：拖动、贴边分屏、双击放大还原、
        最大化后拖走回到鼠标底下，连光标形状和动画都是原生的。网页控件铺满了整个客户区，
        系统的窗口过程根本看不见这一按，所以只能由页面转告。

        页面只报告事实（哪一步、按在哪），判单击还是双击由后端照系统的判据说：
          down     按下：登记位置和时间，窗口一动不动。这一按和上一按挨得够近够快，就直接判成双击，
                   标题栏上就按系统的方式放大/还原（ShowWindow，和右上角按钮同一条路）。
                   连击数不能问浏览器：第一按只要手抖过了拖动阈值就得交给系统，系统的模态循环会把
                   松开吃掉，浏览器从此认定左键还按着，第二下再也数不出来，双击放大就没了。
          move     挪过了系统认定的拖动距离（SM_CXDRAG，页面照 /api/desktop/state 里的数判）：
                   这才把这一按交给系统的拖动/缩放循环，起点用 down 时登记的那个位置，窗口不会慢半拍。
        按下之后没挪够就松手，页面什么都不再发，窗口也一动不动——单击标题栏本来就不该动窗口。
        """
        data = payload or {}
        target = data.get("target")
        code = HT_TARGETS.get(target)
        if code is None:
            raise ValueError("未知的按下位置")
        hwnd = self.hwnd()
        if not hwnd:
            return {"ok": False}
        user32 = ctypes.windll.user32
        user32.SendMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_long]
        phase = data.get("phase") or "move"
        if phase == "down":
            now = time.time()
            point = cursor_pos()
            prev = self._last_down
            self._armed_press = None
            self._dblclk_press = False
            if prev and prev["target"] == target and second_click(hwnd, prev, point, now):
                self._last_down = None
                self._dblclk_press = True  # 双击已经处理了，这一下余下的挪动不能再当拖动
                if target == "caption":
                    # 和右上角最大按钮同一条路。手投 WM_NCLBUTTONDBLCLK 让系统重放标题栏双击，
                    # 真机上（左键还按着、鼠标捕获在网页控件手里）它不动窗口，只有测试环境里偶然生效。
                    self.toggle_maximize()
                return self._note_press(target, phase, {"ok": True, "action": "dblclk"})
            self._last_down = {"target": target, "point": point, "at": now}
            self._armed_press = {"point": point, "at": now}
            return self._note_press(target, phase, {"ok": True, "action": "armed"})
        if self._dblclk_press:
            self._dblclk_press = False
            return self._note_press(target, phase, {"ok": True, "action": "dblclk"})
        if self._loop_running:
            return self._note_press(target, phase, {"ok": True, "action": "busy"})
        armed = self._armed_press
        self._armed_press = None
        self._loop_running = True
        self._last_press = None
        started = _size_move["entered"]

        def start_native_drag():
            # 这一按必须在窗口自己那条线程上交给系统：鼠标捕获是按线程记的，在 HTTP 线程上
            # ReleaseCapture 放不掉网页控件手里那一份，系统的模态循环就拿不到鼠标，表现为完全拖不动。
            record = {"uiThread": is_ui_thread(hwnd), "loops": 0, "ms": 0, "armed": bool(armed)}
            self._last_press = record
            try:
                # 左键已经松开就别交给系统了：它的缩放循环会一直等下一次松开，等不到就把窗口线程钉死
                if not button_down():
                    record["skipped"] = "button-up"
                    return
                x, y = armed["point"] if armed else cursor_pos()
                record["capture"] = user32.GetCapture()
                record["released"] = bool(user32.ReleaseCapture())
                record["cursor"] = [x, y]
                record["loops"] = -1  # 进了系统那一圈循环，松手才会回来
                began = time.time()
                user32.SendMessageW(ctypes.c_void_p(hwnd), WM_NCLBUTTONDOWN, code, (y << 16) | (x & 0xFFFF))
                record["loops"] = _size_move["entered"] - started
                record["ms"] = int((time.time() - began) * 1000)
                record["inside"] = _size_move["inside"]
            finally:
                self._loop_running = False

        self.run_in_ui_thread(hwnd, start_native_drag)
        # 等这一按落到窗口线程上再回话：真拖动时这条请求不会等松手，循环一开始就有结果了
        for _ in range(40):
            if self._last_press is not None:
                break
            time.sleep(0.005)
        reply = {"ok": True, "action": "loop"}
        if self._last_press is None:
            reply["pending"] = True  # 窗口线程正忙着，这一按还在排队
            self._loop_running = False
        else:
            reply.update(self._last_press)
        return self._note_press(target, phase, reply)

    def _note_press(self, target, phase, reply):
        """把这一按记进流水（最近几按）：真机上「双击没反应」这种事只能照它复盘，不用再猜。"""
        self._press_log.append(
            {"target": target, "phase": phase, "action": reply.get("action"), "at": round(time.time(), 3)}
        )
        del self._press_log[:-12]
        return reply

    def run_in_ui_thread(self, hwnd, action):
        try:
            from System import Func, Type
            from webview.platforms.winforms import BrowserView

            instance = BrowserView.instances.get(self.window.uid)
            if instance is not None:
                instance.BeginInvoke(Func[Type](action))
                return
        except Exception as e:
            print(f"窗口线程调度失败：{e}")
        threading.Thread(target=action, daemon=True).start()

    def toggle_maximize(self):
        """最大化/还原交给系统切状态，Win11 的展开与收回动画才有。"""
        hwnd = self.hwnd()
        if not hwnd:
            return
        target = not self.maximized
        command = SW_RESTORE if target is False else SW_MAXIMIZE
        user32 = ctypes.windll.user32

        def apply_state():
            # 交给 UI 线程的回调不能返回值：委托声明的是空返回，返回整数会让进程崩掉
            user32.ShowWindow(ctypes.c_void_p(hwnd), command)

        self.run_in_ui_thread(hwnd, apply_state)
        # 切状态是丢回 UI 线程做的，等它落地再回话，否则页面上的按钮图标会慢一拍
        for _ in range(25):
            if self.maximized == target:
                break
            time.sleep(0.02)

    # ---- 任务栏文字与关闭

    def api_title(self, payload):
        """把当前存档名写进任务栏与 Alt+Tab 的文字里。"""
        world = str((payload or {}).get("text") or "").strip()
        text = f"{APP_TITLE} · {world}"[:120] if world else APP_TITLE
        if self.window is not None:
            try:
                set_native_title(self.window.uid, text)
            except Exception as e:
                print(f"标题更新失败：{e}")
        return {"ok": True}

    def api_quit(self, payload=None):
        self.quit()
        return {"ok": True}

    def handle_closing(self):
        """closing 事件入口：任何异常都不能把窗口卡在关不掉的状态。"""
        try:
            # 关窗前窗还活着：这是记下位置和大小最可靠的一刻（缩到托盘被唤回后还会再记一次）
            self.remember_window()
            return self._decide_closing()
        except Exception as e:
            print(f"关闭询问失败：{e}")
            return None

    def _decide_closing(self):
        """拦所有关闭入口（窗口关闭按钮、Alt+F4、任务栏）：备份中先警告，再按设置处理。"""
        if self._allow_close:
            self._allow_close = False
            return None
        if self.setup_required or not ICON_FILE.is_file():
            return None  # 还没选存放位置、或没有托盘图标：没有可挽留的
        if server.backup_running():
            keep = self.window.create_confirmation_dialog(
                "备份还没有结束",
                "现在退出会中断本次备份。确定要退出吗？",
            )
            return None if keep else False
        mode = self.settings.get(ON_CLOSE_SETTING, CLOSE_ASK)
        if mode == CLOSE_TRAY:
            self.hide_to_tray()
            return False
        if mode == CLOSE_EXIT:
            return None
        # 每次询问：先取消关闭，让页面弹出选择框
        threading.Thread(target=self.push, args=("DesktopCloseAsk", {}), daemon=True).start()
        return False

    def remember_window(self):
        """记下窗口矩形；最大化时记的是还原后的矩形，下次不会按满屏尺寸打开。"""
        hwnd = self.hwnd()
        if hwnd:
            save_window_rect(self.data_dir, hwnd)

    def api_close_choice(self, payload):
        data = payload or {}
        choice = data.get("choice")
        if choice not in (CLOSE_TRAY, CLOSE_EXIT):
            raise ValueError("未知的关闭方式")
        if data.get("remember"):
            self.settings[ON_CLOSE_SETTING] = choice
            self._save_settings()
        if choice == CLOSE_TRAY:
            self.hide_to_tray()
        else:
            self.quit()
        return {"settings": dict(self.settings)}

    def quit(self):
        if self.window is not None:
            self._allow_close = True
            self.window.destroy()

    def hide_to_tray(self):
        """先确认托盘图标挂上了，再藏窗口：挂不上就退回任务栏最小化，免得窗口找不回来。"""
        if self.ensure_tray().start():
            self.window.hide()
        else:
            self.window.minimize()

    def toggle_from_tray(self):
        """点托盘图标：藏起来就唤回，显示中就收起。图标一直留着，免得窗口反而找不见。"""
        if self.window_hidden():
            self.window.show()
        else:
            self.window.hide()

    def window_hidden(self):
        return not ctypes.windll.user32.IsWindowVisible(self.hwnd())

    def api_wake(self, payload=None):
        """重复启动被拦下时，第二个实例打这个接口：把窗口带回前台，它自己退出去。"""
        self.bring_to_front()
        return {"ok": True}

    def bring_to_front(self):
        if self.window is not None and self.window_hidden():
            self.window.show()
        hwnd = self.hwnd()
        if not hwnd:
            return
        user32 = ctypes.windll.user32

        def raise_window():
            # 交给 UI 线程的回调不能返回值，否则进程会崩在委托转换上
            if user32.IsIconic(ctypes.c_void_p(hwnd)):
                user32.ShowWindow(ctypes.c_void_p(hwnd), SW_RESTORE)
            user32.SetForegroundWindow(ctypes.c_void_p(hwnd))
            if user32.GetForegroundWindow() != hwnd:
                # 前台切换权限被系统卡住时，用切换活动窗口的老办法兜底
                user32.SwitchToThisWindow(ctypes.c_void_p(hwnd), True)

        self.run_in_ui_thread(hwnd, raise_window)
        for _ in range(50):
            if not self.window_hidden():
                break
            time.sleep(0.02)

    def ensure_tray(self):
        if self.tray is None:
            self.tray = TrayIcon(ICON_FILE, APP_TITLE, self.toggle_from_tray, self.quit)
        return self.tray

    # ---- 界面设置

    def api_settings(self, payload):
        data = payload or {}
        if ON_CLOSE_SETTING in data:
            value = data.get(ON_CLOSE_SETTING)
            if value not in CLOSE_CHOICES:
                raise ValueError("未知的关闭行为")
            self.settings[ON_CLOSE_SETTING] = value
            self._save_settings()
            if value != CLOSE_TRAY and self.tray is not None:
                self.tray.stop()
                self.tray = None  # 下次要收托盘时重新起一个，托盘线程不能复用
        return {"settings": dict(self.settings)}

    # ---- 数据目录

    def api_setup(self, payload):
        mode = (payload or {}).get("mode")
        if mode not in ("portable", "appdata"):
            raise ValueError("未知的存放位置")
        path = portable_dir() if mode == "portable" else appdata_dir()
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".write-probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
        except OSError as e:
            raise ValueError(f"这个位置写不进去：{e}")
        write_marker(path, mode)
        clear_markers(path)
        self.remember_window()  # 换数据目录也把窗口位置和大小带过去
        carry_user_files(self.data_dir, path)
        argv = ["--data-dir", str(path), "--import-profile", str(self.data_dir / PROFILE_DIR_NAME),
                "--takeover"]  # 老实例还握着锁，新实例直接接手，别把它当成重复启动
        if self.pending_world:
            argv += ["--world", self.pending_world]
        if self.args.verbose:
            argv.append("--verbose")
        self.restart(argv)
        return {"ok": True, "dataDir": str(path)}

    def restart(self, argv):
        threading.Thread(target=self._restart_later, args=(argv,), daemon=True).start()

    def _restart_later(self, argv):
        time.sleep(0.6)  # 等响应回到页面，让「正在重启」看得见
        try:
            spawn_instance(argv)
        except OSError as e:
            print(f"重启失败：{e}")
            return
        try:
            if self.httpd is not None:
                server.stop_server(self.httpd)
                self.httpd = None
        except Exception:
            pass
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.flush()
            except Exception:
                pass
        os._exit(0)

    # ---- 拖入存档

    def handle_drop(self, event):
        paths = dropped_paths(event)
        if not paths:
            return
        world = resolve_world_dir(paths[0])
        if self.setup_required:
            self.pending_world = world
        self.push("DesktopDrop", {"paths": [world], "deferred": self.setup_required})

    def push(self, name, payload):
        if self.window is None:
            return
        script = (
            "window.%s && window.%s(%s)"
            % (name, name, json.dumps(payload, ensure_ascii=False))
        )
        try:
            self.window.evaluate_js(script)
        except Exception as e:
            print(f"推送消息到页面失败：{e}")

    def register_drop(self):
        if self._drop_registered or self.window is None:
            return
        self._drop_registered = True
        try:
            self.window.dom.body.on("drop", self.handle_drop)
        except Exception as e:
            print(f"拖拽支持不可用：{e}")

    def shutdown(self):
        self.remember_window()
        if self.tray is not None:
            self.tray.stop()


def dropped_paths(event):
    """拖进来的路径：先取 DOM 事件带的路径，再用 WebView2 原生投递的兜底。"""
    paths = []
    transfer = (event or {}).get("dataTransfer") or {}
    for item in transfer.get("files") or []:
        path = item.get("pywebviewFullPath") if isinstance(item, dict) else None
        if path:
            paths.append(unquote(path))
    try:
        from webview.dom import _dnd_state

        remaining = list(_dnd_state["paths"])
        del _dnd_state["paths"][:]
    except Exception:
        remaining = []
    for _, path in remaining:
        path = unquote(path)
        if path not in paths:
            paths.append(path)
    return paths


def resolve_world_dir(path):
    """把拖进来的路径归一成存档目录（能找到 level.dat 就往上/下走一层）。"""
    candidate = Path(path)
    if candidate.is_file():
        candidate = candidate.parent
    if (candidate / "level.dat").exists():
        return str(candidate)
    try:
        children = sorted(p for p in candidate.iterdir() if p.is_dir())
    except OSError:
        return str(candidate)
    for child in children:
        if (child / "level.dat").exists():
            return str(child)
    return str(candidate)


def spawn_instance(argv):
    program = [str(sys.executable)] if FROZEN else [str(sys.executable), str(Path(__file__).resolve())]
    creationflags = 0
    if sys.platform == "win32":
        creationflags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    devnull = open(os.devnull, "w", encoding="utf-8")
    subprocess.Popen(
        program + argv,
        cwd=str(PROGRAM_DIR),
        stdin=devnull,
        stdout=devnull,
        stderr=devnull,
        close_fds=True,
        creationflags=creationflags,
    )


ERROR_ALREADY_EXISTS = 183
STILL_ACTIVE_WAIT = 0x00000102  # WaitForSingleObject 超时：进程还在
PROCESS_SYNCHRONIZE = 0x00100000
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_kernel32.CreateMutexW.restype = wintypes.HANDLE
_kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
_kernel32.OpenProcess.restype = wintypes.HANDLE
_kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
_kernel32.WaitForSingleObject.restype = wintypes.DWORD
_kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
_kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
_instance_mutex = None


def instance_key(data_dir):
    """一把数据目录一把锁：同一份数据只开一个窗口，测试用的临时目录之间互不影响。"""
    digest = hashlib.sha1(str(data_dir).lower().encode("utf-8")).hexdigest()[:16]
    return "Local\\PartialBackuper-" + digest


def acquire_instance_lock(data_dir):
    """抢本实例的命名互斥体。返回 False 表示已经有另一个实例在用同一份数据。"""
    global _instance_mutex
    if _instance_mutex:
        return True
    ctypes.set_last_error(0)
    handle = _kernel32.CreateMutexW(None, False, instance_key(data_dir))
    if not handle:
        return True  # 连句柄都拿不到，就别拦用户启动
    _instance_mutex = handle
    return ctypes.get_last_error() != ERROR_ALREADY_EXISTS


def lock_file(data_dir):
    return Path(data_dir) / LOCK_NAME


def write_lock(data_dir, port):
    """把端口、进程号和接口令牌留在数据目录里，下一个实例靠它找到并唤回这一个。"""
    try:
        lock_file(data_dir).write_text(
            json.dumps({"pid": os.getpid(), "port": port, "token": server.API_TOKEN}),
            encoding="utf-8")
    except OSError as e:
        print(f"记录实例信息失败：{e}")


def clear_lock(data_dir):
    try:
        lock_file(data_dir).unlink()
    except OSError:
        pass


def read_lock(data_dir):
    try:
        data = json.loads(lock_file(data_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def pid_alive(pid):
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    handle = _kernel32.OpenProcess(PROCESS_SYNCHRONIZE, False, pid)
    if not handle:
        return False
    try:
        return _kernel32.WaitForSingleObject(handle, 0) == STILL_ACTIVE_WAIT
    finally:
        _kernel32.CloseHandle(handle)


def wake_running_instance(data_dir):
    """通知已经在跑的那个实例「有人又点开你了」，让它把窗口带回前台。"""
    lock = read_lock(data_dir)
    if not lock or not pid_alive(lock.get("pid")):
        return False
    port = lock.get("port")
    if not isinstance(port, int):
        return False
    try:
        headers = {"Content-Type": "application/json"}
        token = lock.get("token")
        if isinstance(token, str) and token:
            headers["X-PB-Token"] = token
        request = urllib.request.Request(
            "http://127.0.0.1:%d/api/desktop/wake" % port,
            data=b"{}",
            headers=headers,
        )
        with urllib.request.urlopen(request, timeout=3) as response:
            body = json.loads(response.read().decode("utf-8") or "{}")
        return bool(body.get("ok"))
    except Exception as e:
        print(f"唤回已有实例失败：{e}")
        return False


def run_desktop(args):
    data_dir, mode, setup_required = resolve_data_dir(args)
    if not acquire_instance_lock(data_dir) and not args.takeover:
        if wake_running_instance(data_dir):
            print("已经有实例在运行，已把它的窗口带回前台。")
            return 0
        print("检测到同目录的旧实例信息，但没能唤回，按新实例启动。")

    server.VERBOSE = args.verbose
    configs_dir = None if FROZEN else PROJECT_DIR / "configs"
    server.configure_storage(data_dir, configs_dir=configs_dir)
    if not setup_required:
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

    bridge = DesktopBridge(args, data_dir, mode, setup_required)
    if args.import_profile:
        migrate_profile(args.import_profile, data_dir / PROFILE_DIR_NAME)

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
    write_lock(data_dir, port)

    geometry = startup_rect(data_dir)
    bridge.start_rect = physical_rect(geometry)
    window = webview.create_window(
        APP_TITLE,
        url=f"http://127.0.0.1:{port}/",
        width=geometry["width"],
        height=geometry["height"],
        x=geometry["x"],
        y=geometry["y"],
        min_size=MIN_WINDOW_SIZE,
        background_color="#080b10",
        frameless=True,
        easy_drag=False,
    )
    bridge.attach(window, httpd)
    server.set_desktop(bridge)
    window.events.closing += bridge.handle_closing
    window.events.shown += bridge.apply_start_rect
    window.events.loaded += bridge.register_drop
    window.events.loaded += bridge.install_native_window
    print(f"{APP_TITLE} · 数据目录（{mode}）：{data_dir}")
    try:
        webview.start(
            gui="edgechromium",
            debug=args.verbose,
            private_mode=False,
            storage_path=str(data_dir / PROFILE_DIR_NAME),
            icon=str(ICON_FILE) if ICON_FILE.is_file() else None,
        )
    finally:
        server.set_desktop(None)
        bridge.shutdown()
        clear_lock(data_dir)
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
