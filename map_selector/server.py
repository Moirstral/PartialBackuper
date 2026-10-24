import argparse
import concurrent.futures
import glob
import gzip
import hashlib
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import webbrowser
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from renderer import read_chunk_activity, read_gzip_nbt, read_region_chunk, render_tile_gz

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
PUBLIC_DIR = BASE_DIR / "public"
CACHE_DIR = BASE_DIR / ".cache"
CONFIG_FILE = BASE_DIR / "world.json"
CONFIGS_DIR = PROJECT_DIR / "configs"
BACKUP_RUNNER = PROJECT_DIR / "backup_runner.py"
REGION_RE = re.compile(r"^r\.(-?\d+)\.(-?\d+)\.mca$")
DIM_RE = re.compile(r"[^A-Za-z0-9_.-]+")
JSON_SUFFIX = ".json"
SECTOR_SIZE = 4096
DEFAULT_PORT = 8787

VANILLA_DIMS = {
    "minecraft:overworld": ("主世界", 0),
    "minecraft:the_nether": ("下界", 1),
    "minecraft:the_end": ("末地", 2),
}

XAERO_DIMS = {
    "dim%0": "minecraft:overworld",
    "dim%-1": "minecraft:the_nether",
    "dim%1": "minecraft:the_end",
}

XAERO_COLORS = [
    "#000000", "#0000aa", "#00aa00", "#00aaaa",
    "#aa0000", "#aa00aa", "#ffaa00", "#aaaaaa",
    "#555555", "#5555ff", "#55ff55", "#55ffff",
    "#ff5555", "#ff55ff", "#ffff55", "#ffffff",
    "#f45ac8", "#58c8ff", "#8cff3f", "#ff8fb3", "#a36a3f",
]

STATE_LOCK = threading.Lock()
WORLD_DATA = None
PENDING_LOCK = threading.Lock()
PENDING = {}
EXECUTOR = None
VERBOSE = False
BACKUP_LOCK = threading.Lock()
BACKUP_JOB = None

SHUTDOWN_GRACE = 1.0  # 页面关闭上报后等待的秒数（保持短暂，关页即停）
PAGE_TIMEOUT = 1800.0  # 心跳超时多久后回收 SID（仅清理内存，不触发停服）
FRESH_WINDOW = 6.0  # 多久内有心跳算页面仍活跃（略大于前端 5 秒心跳间隔）

SERVER_LOCK = threading.Lock()
ACTIVE_PAGES = {}  # sid -> last_seen
PENDING_CLOSE_AT = None  # 最近一次“页面关闭”上报时间


def touch_page(sid):
    global PENDING_CLOSE_AT
    if not sid:
        return
    with SERVER_LOCK:
        now = time.time()
        # 仍有页面在发心跳，取消待关闭
        PENDING_CLOSE_AT = None
        if sid not in ACTIVE_PAGES:
            # 新 SID 加入：如果所有现有 SID 都超过 3 秒没心跳，判定为刷新残留
            if ACTIVE_PAGES and all(now - t > 3.0 for t in ACTIVE_PAGES.values()):
                if VERBOSE:
                    stale = [s[:8] for s in ACTIVE_PAGES]
                    print(f"[touch] 新页面加入，清理刷新残留 SID: {stale}")
                ACTIVE_PAGES.clear()
        ACTIVE_PAGES[sid] = now


def report_page_closed(sid):
    """页面关闭上报：移除该页面并进入待关闭状态。

    停服由这个显式上报驱动，而不是“活跃页面数为 0”，
    这样刷新残留的 SID 不会被误当成“还有页面开着”。
    """
    global PENDING_CLOSE_AT
    with SERVER_LOCK:
        if sid:
            ACTIVE_PAGES.pop(sid, None)
        PENDING_CLOSE_AT = time.time()


def note_navigation():
    """刷新/新标签会重新请求首页，此时不应把旧页面的关闭上报当作停服信号。"""
    global PENDING_CLOSE_AT
    with SERVER_LOCK:
        PENDING_CLOSE_AT = None


def shutdown_watcher(httpd):
    global PENDING_CLOSE_AT
    while True:
        time.sleep(0.2)
        now = time.time()
        with SERVER_LOCK:
            dead = [sid for sid, t in ACTIVE_PAGES.items() if now - t > PAGE_TIMEOUT]
            for sid in dead:
                ACTIVE_PAGES.pop(sid, None)
            pending = PENDING_CLOSE_AT
            if pending is not None and any(
                now - t <= FRESH_WINDOW for t in ACTIVE_PAGES.values()
            ):
                # 还有别的页面在正常心跳（例如多标签页），取消关闭
                PENDING_CLOSE_AT = None
                pending = None

        if pending is None or now - pending < SHUTDOWN_GRACE:
            continue
        with BACKUP_LOCK:
            backup_running = BACKUP_JOB is not None and BACKUP_JOB["running"]
        if backup_running:
            # 备份进行中不自动停服，等它结束后再判断
            continue
        print("\n所有页面已关闭，正在停止服务器…")
        httpd.shutdown()
        return

class WorldData:
    __slots__ = ("info", "index", "hash", "json")

    def __init__(self, info, index, world_hash):
        self.info = info
        self.index = index
        self.hash = world_hash
        self.json = json.dumps(info, ensure_ascii=False).encode("utf-8")


def world_hash(path):
    return hashlib.sha1(path.encode("utf-8")).hexdigest()[:12]


def safe_dim_dir(dim_id):
    return DIM_RE.sub("_", dim_id)


def scan_chunk_mask(path):
    try:
        with path.open("rb") as fh:
            head = fh.read(4096)
    except OSError:
        return "", 0
    if len(head) < 4096:
        return "", 0
    mask = bytearray(128)
    count = 0
    for i in range(1024):
        base = i * 4
        if head[base + 3] and (head[base] or head[base + 1] or head[base + 2]):
            mask[i >> 3] |= 1 << (i & 7)
            count += 1
    return mask.hex(), count


def scan_region_dir(region_dir, dim_id):
    regions = []
    index = {}
    if not region_dir.is_dir():
        return regions, index
    for f in region_dir.iterdir():
        m = REGION_RE.match(f.name)
        if not m:
            continue
        try:
            st = f.stat()
        except OSError:
            continue
        rx = int(m.group(1))
        rz = int(m.group(2))
        chunks, chunk_count = scan_chunk_mask(f)
        regions.append({
            "x": rx,
            "z": rz,
            "size": st.st_size,
            "mtime": st.st_mtime_ns // 1000,
            "chunks": chunks,
            "chunkCount": chunk_count,
        })
        index[(dim_id, rx, rz)] = {
            "path": str(f),
            "nether": dim_id == "minecraft:the_nether",
        }
    regions.sort(key=lambda r: (r["x"], r["z"]))
    return regions, index


ACTIVITY_LOCK = threading.Lock()
ACTIVITY_CACHE = {}


def read_external_chunk(region_path, rx, rz, idx, scheme):
    name = f"c.{rx * 32 + idx % 32}.{rz * 32 + idx // 32}.mcc"
    try:
        blob = (region_path.parent / name).read_bytes()
    except OSError:
        return None
    candidates = [blob]
    if blob[:1] and blob[0] in (1, 2, 3, 129, 130, 131):
        candidates.append(blob[1:])
    for payload in candidates:
        for kind in (scheme, 2, 1, 3):
            try:
                if kind == 2:
                    raw = zlib.decompress(payload)
                elif kind == 1:
                    raw = gzip.decompress(payload)
                else:
                    raw = payload
            except Exception:
                continue
            if raw[:1] == b"\x0a":
                return raw
    return None


def read_activity_chunk(region_path, data, idx, rx, rz):
    base = idx * 4
    offset = (data[base] << 16) | (data[base + 1] << 8) | data[base + 2]
    sectors = data[base + 3]
    if not offset or not sectors:
        return None
    pos = offset * SECTOR_SIZE
    if pos + 5 > len(data):
        return None
    comp = data[pos + 4]
    if comp >= 128:
        return read_external_chunk(region_path, rx, rz, idx, comp - 128)
    return read_region_chunk(data, idx)


def scan_region_activity(region_path, rx, rz):
    result = {"x": rx, "z": rz, "times": [], "unreadable": 0, "failed": False}
    try:
        stat = region_path.stat()
    except OSError:
        result["failed"] = True
        return result
    mtime = stat.st_mtime_ns // 1000
    key = (str(region_path), mtime)
    with ACTIVITY_LOCK:
        cached = ACTIVITY_CACHE.get(key)
    if cached is not None:
        return cached

    data = None
    for _ in range(2):
        try:
            data = region_path.read_bytes()
            after = region_path.stat().st_mtime_ns // 1000
        except OSError:
            result["failed"] = True
            return result
        if after == mtime:
            break
        mtime = after
        key = (str(region_path), mtime)
        data = None
    if data is None or len(data) < SECTOR_SIZE:
        result["failed"] = True
        return result

    times = []
    unreadable = 0
    for idx in range(1024):
        base = idx * 4
        if not data[base + 3] or not (data[base] or data[base + 1] or data[base + 2]):
            continue
        raw = read_activity_chunk(region_path, data, idx, rx, rz)
        if raw is None:
            unreadable += 1
            continue
        try:
            value = read_chunk_activity(raw)
        except Exception:
            unreadable += 1
            continue
        if value and value > 0:
            times.append([idx, int(value)])
    result.update({"times": times, "unreadable": unreadable})
    with ACTIVITY_LOCK:
        if len(ACTIVITY_CACHE) > 2000:
            ACTIVITY_CACHE.clear()
        ACTIVITY_CACHE[key] = result
    return result


def scan_dim_activity(wd, dim, min_seconds=0):
    started = time.time()
    region_dir = Path(wd.info["path"]) / dim["folder"]
    regions = dim.get("regions", [])
    results = []
    failed = 0
    if regions:
        workers = min(6, max(1, len(regions)))
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [
                pool.submit(
                    scan_region_activity,
                    region_dir / f"r.{region['x']}.{region['z']}.mca",
                    region["x"],
                    region["z"],
                )
                for region in regions
            ]
            for future in concurrent.futures.as_completed(futures):
                try:
                    results.append(future.result())
                except Exception:
                    failed += 1

    threshold = max(0, int(round(min_seconds * 20)))
    payload = []
    for result in results:
        kept = [item for item in result["times"] if item[1] >= threshold]
        if not kept:
            continue
        mask = bytearray(128)
        for idx, _ticks in kept:
            mask[idx >> 3] |= 1 << (idx & 7)
        payload.append(
            {
                "x": result["x"],
                "z": result["z"],
                "mask": mask.hex(),
                "count": len(kept),
                "times": kept,
            }
        )
    payload.sort(key=lambda item: (item["x"], item["z"]))
    return {
        "dim": dim["id"],
        "label": dim["label"],
        "folder": dim["folder"],
        "regionCount": len(regions),
        "minSeconds": min_seconds,
        "minTicks": threshold,
        "activeRegions": len(payload),
        "activeChunks": sum(item["count"] for item in payload),
        "failedRegions": failed + sum(1 for result in results if result["failed"]),
        "unreadableChunks": sum(result["unreadable"] for result in results),
        "regions": payload,
        "elapsed": round(time.time() - started, 2),
    }


def normalize_path_input(value):
    """Return a user-supplied path in POSIX form (accepts \\, quotes, padding)."""
    if not isinstance(value, str):
        return ""
    text = value.strip()
    while len(text) > 1 and text[0] in "\"'" and text[-1] == text[0]:
        text = text[1:-1].strip()
    return text.replace("\\", "/")


def build_world(path_str):
    p = Path(os.path.expanduser(normalize_path_input(path_str))).resolve()
    if not p.is_dir():
        raise ValueError("文件夹不存在")
    level_file = p / "level.dat"
    if not level_file.is_file():
        raise ValueError("不是有效的存档目录（缺少 level.dat）")

    name = p.name
    version = ""
    data_version = None
    game_type = None
    hardcore = False
    allow_commands = False
    last_played = None
    # Minecraft rewrites level.dat while saving; retry a few times instead of
    # showing blank version info when the file was caught mid-write.
    for attempt in range(3):
        try:
            root = read_gzip_nbt(level_file.read_bytes())
            data = root.get("Data") if isinstance(root, dict) else None
            if isinstance(data, dict):
                if isinstance(data.get("LevelName"), str) and data["LevelName"]:
                    name = data["LevelName"]
                ver = data.get("Version")
                if isinstance(ver, dict) and isinstance(ver.get("Name"), str):
                    version = ver["Name"]
                if isinstance(data.get("DataVersion"), int):
                    data_version = data["DataVersion"]
                if isinstance(data.get("GameType"), int):
                    game_type = data["GameType"]
                hardcore = bool(data.get("hardcore"))
                allow_commands = bool(data.get("allowCommands"))
                last_played = data.get("LastPlayed")
            break
        except Exception:
            if attempt == 2:
                break
            time.sleep(0.08)

    # LastPlayed is epoch milliseconds; old or modded saves can hold tick counts.
    last_played_ms = (
        int(last_played)
        if isinstance(last_played, int) and 10**12 <= last_played < 4 * 10**12
        else 0
    )

    icon = p / "icon.png"
    has_icon = icon.is_file()
    icon_mtime = int(icon.stat().st_mtime_ns // 1000) if has_icon else 0

    dims = []
    index = {}
    seen = set()

    def add_dim(dim_id, label, rel_folder, order):
        region_dir = p / rel_folder
        regions, idx = scan_region_dir(region_dir, dim_id)
        index.update(idx)
        seen.add(dim_id)
        bounds = None
        if regions:
            bounds = {
                "x1": min(r["x"] for r in regions),
                "z1": min(r["z"] for r in regions),
                "x2": max(r["x"] for r in regions),
                "z2": max(r["z"] for r in regions),
            }
        dims.append({
            "id": dim_id,
            "label": label,
            "folder": rel_folder,
            "order": order,
            "regionCount": len(regions),
            "chunkCount": sum(r["chunkCount"] for r in regions),
            "bytes": sum(r["size"] for r in regions),
            "bounds": bounds,
            "regions": regions,
        })

    new_root = p / "dimensions"
    candidates = []
    if new_root.is_dir():
        for ns_dir in new_root.iterdir():
            if not ns_dir.is_dir():
                continue
            for d in ns_dir.iterdir():
                if not d.is_dir():
                    continue
                if not (d / "region").is_dir():
                    continue
                dim_id = f"{ns_dir.name}:{d.name}"
                label, order = VANILLA_DIMS.get(dim_id, (f"{ns_dir.name}:{d.name}", 10))
                candidates.append((order, dim_id, label, f"dimensions/{ns_dir.name}/{d.name}/region"))
    candidates.sort(key=lambda c: (c[0], c[1]))
    for order, dim_id, label, rel in candidates:
        add_dim(dim_id, label, rel, order)

    legacy = [
        ("minecraft:overworld", "主世界", "region", 0),
        ("minecraft:the_nether", "下界", "DIM-1/region", 1),
        ("minecraft:the_end", "末地", "DIM1/region", 2),
    ]
    for dim_id, label, rel, order in legacy:
        if dim_id in seen:
            continue
        if (p / rel).is_dir():
            add_dim(dim_id, label, rel, order)

    dims.sort(key=lambda d: (d["order"], d["label"]))

    info = {
        "path": p.as_posix(),
        "name": name,
        "version": version,
        "dataVersion": data_version,
        "gameType": game_type,
        "hardcore": hardcore,
        "allowCommands": allow_commands,
        "lastPlayedMs": last_played_ms,
        "hasIcon": has_icon,
        "iconMtime": icon_mtime,
        "dimensions": dims,
    }
    return WorldData(info, index, world_hash(p.as_posix()))


def load_world(path_str, persist=True):
    global WORLD_DATA
    wd = build_world(path_str)
    with STATE_LOCK:
        WORLD_DATA = wd
    if persist:
        try:
            CONFIG_FILE.write_text(
                json.dumps({"path": wd.info["path"]}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass
    return wd


def get_world():
    return WORLD_DATA


def xaero_world_dir(info):
    save_path = Path(info["path"])
    names = [save_path.name.casefold()]
    level_name = info.get("name")
    if isinstance(level_name, str) and level_name.strip():
        names.append(level_name.strip().casefold())
    bases = []
    for root in (save_path.parent.parent, save_path.parent):
        base = root / "xaero" / "minimap"
        if base.is_dir() and base not in bases:
            bases.append(base)
    for base in bases:
        try:
            entries = list(base.iterdir())
        except OSError:
            continue
        for entry in entries:
            if entry.is_dir() and entry.name.casefold() in names:
                return entry
    return None


def parse_xaero_waypoints(path):
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return []
    points = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("waypoint:"):
            continue
        fields = line.split(":")
        if len(fields) < 14:
            continue
        name = ":".join(fields[1:-12]).strip()
        if not name:
            continue
        try:
            x = float(fields[-11])
            z = float(fields[-9])
        except ValueError:
            continue
        if fields[-7].strip().lower() == "true":
            continue
        y = None
        if fields[-10] not in ("", "~"):
            try:
                y = float(fields[-10])
            except ValueError:
                pass
        try:
            color = XAERO_COLORS[int(fields[-8])]
        except (ValueError, IndexError):
            color = XAERO_COLORS[15]
        points.append({
            "name": name,
            "initials": fields[-12],
            "x": int(x) if x.is_integer() else x,
            "y": int(y) if y is not None and y.is_integer() else y,
            "z": int(z) if z.is_integer() else z,
            "color": color,
        })
    return points


def read_xaero_waypoints(wd):
    result = {
        "available": False,
        "worldDir": "",
        "dimensions": {},
        "total": 0,
    }
    world_dir = xaero_world_dir(wd.info)
    if world_dir is None:
        return result
    result["available"] = True
    result["worldDir"] = str(world_dir)
    total = 0
    try:
        entries = list(world_dir.iterdir())
    except OSError:
        return result
    for entry in entries:
        dim_id = XAERO_DIMS.get(entry.name)
        if dim_id is None or not entry.is_dir():
            continue
        points = parse_xaero_waypoints(entry / "waypoints.txt")
        if points:
            result["dimensions"][dim_id] = points
            total += len(points)
    result["total"] = total
    return result


def tile_cache_path(wd, dim_id, rx, rz, mtime, size):
    safe = safe_dim_dir(dim_id)
    return CACHE_DIR / wd.hash / safe / f"{rx}.{rz}.{mtime}.{size}.rgba.gz"


def get_tile(wd, dim_id, rx, rz, size):
    item = wd.index.get((dim_id, rx, rz))
    if item is None:
        return None
    dim = next((d for d in wd.info["dimensions"] if d["id"] == dim_id), None)
    if dim is None:
        return None
    region = next((r for r in dim["regions"] if r["x"] == rx and r["z"] == rz), None)
    if region is None:
        return None
    cache_path = tile_cache_path(wd, dim_id, rx, rz, region["mtime"], size)
    try:
        if cache_path.is_file():
            return cache_path.read_bytes()
    except OSError:
        pass

    key = str(cache_path)
    with PENDING_LOCK:
        future = PENDING.get(key)
        if future is None:
            future = EXECUTOR.submit(render_tile_gz, item["path"], item["nether"], size)
            PENDING[key] = future
    try:
        gz = future.result()
    finally:
        with PENDING_LOCK:
            PENDING.pop(key, None)

    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache_path.with_name(cache_path.name + f".tmp{threading.get_ident()}")
        tmp.write_bytes(gz)
        os.replace(tmp, cache_path)
    except OSError:
        pass
    return gz


def cleanup_cache():
    cutoff = time.time() - 30 * 24 * 3600
    if not CACHE_DIR.is_dir():
        return
    for f in CACHE_DIR.rglob("*.rgba.gz"):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
        except OSError:
            pass


# ---------------------------------------------------------------- configs

def config_path(name, must_exist=False):
    if not isinstance(name, str) or not name.strip():
        raise ValueError("请选择或输入配置文件名")
    name = name.strip()
    if not name.lower().endswith(JSON_SUFFIX):
        name += JSON_SUFFIX
    if name in (JSON_SUFFIX, "config_template.json") or "/" in name or "\\" in name:
        raise ValueError("配置文件名称无效（不能包含路径，也不能使用模板名）")
    if len(name) > 120:
        raise ValueError("配置文件名过长")
    path = (CONFIGS_DIR / name).resolve()
    if path.parent != CONFIGS_DIR.resolve():
        raise ValueError("配置文件必须位于 configs 目录")
    if must_exist and not path.is_file():
        raise ValueError(f"配置文件 {name} 不存在")
    return path


def read_config_file(path):
    text = path.read_text(encoding="utf-8-sig")
    try:
        cfg = json.loads(text)
    except json.JSONDecodeError as exc:
        # Hand-written configs often paste a Windows path with lone
        # backslashes, which are invalid JSON escapes. Retry with them
        # turned into separators.
        repaired = text.replace("\\\\", "/").replace("\\", "/")
        try:
            cfg = json.loads(repaired)
        except json.JSONDecodeError:
            raise exc
    if not isinstance(cfg, dict):
        raise ValueError("配置必须是 JSON 对象")
    if isinstance(cfg.get("save_path"), str):
        cfg["save_path"] = normalize_path_input(cfg["save_path"])
    return cfg


def list_configs():
    items = []
    if not CONFIGS_DIR.is_dir():
        return items
    for f in sorted(CONFIGS_DIR.iterdir(), key=lambda p: p.name.lower()):
        if not f.is_file() or f.suffix.lower() != JSON_SUFFIX:
            continue
        if f.name == "config_template.json":
            continue
        item = {
            "file": f.name,
            "savePath": "",
            "partialCount": 0,
            "activityCount": 0,
            "mtime": 0,
            "error": None,
        }
        try:
            item["mtime"] = int(f.stat().st_mtime_ns // 1000)
            cfg = read_config_file(f)
            save_path = cfg.get("save_path")
            if isinstance(save_path, str):
                item["savePath"] = save_path
            partials = cfg.get("partials")
            if isinstance(partials, list):
                item["partialCount"] = len(partials)
            activity = cfg.get("activity")
            if isinstance(activity, list):
                item["activityCount"] = len(activity)
            elif isinstance(activity, dict) and isinstance(activity.get("folders"), list):
                item["activityCount"] = len(activity["folders"])
        except Exception as e:
            item["error"] = str(e)
        items.append(item)
    return items


ENTRY_LIMIT = 600
ENTRY_MAX_DEPTH = 6


def list_save_entries(wd):
    """Folders at any depth plus files directly inside the save root, as save-relative paths."""
    root = Path(wd.info["path"])
    entries = []
    truncated = False

    def walk(folder, rel, depth):
        nonlocal truncated
        if depth > ENTRY_MAX_DEPTH:
            return
        try:
            children = sorted(folder.iterdir(), key=lambda p: (p.name.lower(), p.name))
        except OSError:
            return
        for child in children:
            if len(entries) >= ENTRY_LIMIT:
                truncated = True
                return
            path = f"{rel}/{child.name}" if rel else child.name
            try:
                is_dir = child.is_dir()
            except OSError:
                continue
            if is_dir:
                entries.append({"path": path, "type": "dir"})
                walk(child, path, depth + 1)
            elif depth == 1:
                entries.append({"path": path, "type": "file"})

    walk(root, "", 1)
    return {"entries": entries, "truncated": truncated, "limit": ENTRY_LIMIT}


def validate_config(cfg):
    if not isinstance(cfg, dict):
        raise ValueError("配置必须是 JSON 对象")
    save_path = cfg.get("save_path")
    if not isinstance(save_path, str) or not save_path.strip():
        raise ValueError("配置的 save_path 无效")
    save_path = normalize_path_input(save_path)
    cfg["save_path"] = save_path
    ignores = cfg.get("ignores", [])
    if not isinstance(ignores, list):
        raise ValueError("ignores 必须是数组")
    if "partials" not in cfg:
        cfg["partials"] = []
    if not isinstance(cfg["partials"], list):
        raise ValueError("partials 必须是数组")
    for item in cfg["partials"]:
        if isinstance(item, str):
            continue
        if not isinstance(item, dict):
            raise ValueError("partials 中存在无效项")
        folder = item.get("folder", item.get("folders"))
        if folder is not None:
            if not isinstance(folder, str) and not (
                isinstance(folder, list) and all(isinstance(x, str) for x in folder)
            ):
                raise ValueError("partials 的 folder 必须是字符串或字符串数组")
    world = get_world()
    if world is None:
        raise ValueError("尚未加载存档")
    if Path(os.path.expanduser(save_path)).resolve() != Path(world.info["path"]).resolve():
        raise ValueError("配置的 save_path 与当前地图的存档不一致")
    return cfg


def save_config_file(path, cfg):
    CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
    if isinstance(cfg.get("save_path"), str):
        cfg["save_path"] = normalize_path_input(cfg["save_path"])
    backup_name = None
    if path.is_file():
        bak = path.with_name(path.name + ".bak")
        try:
            shutil.copy2(path, bak)
            backup_name = bak.name
        except OSError:
            backup_name = None
    tmp = path.with_name(path.name + f".tmp{os.getpid()}")
    text = json.dumps(cfg, ensure_ascii=False, indent=2) + "\n"
    try:
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
    return backup_name


def find_backup_zip(save_path, started):
    try:
        pattern = glob.escape(save_path.name) + "_*_partial.zip"
        best = None
        for f in save_path.parent.glob(pattern):
            try:
                st = f.stat()
            except OSError:
                continue
            if st.st_mtime >= started - 10 and (best is None or st.st_mtime > best[0]):
                best = (st.st_mtime, f)
        return best[1] if best else None
    except OSError:
        return None


def public_job(job):
    if job is None:
        return None
    with BACKUP_LOCK:
        return {
            "id": job["id"],
            "file": job["file"],
            "running": job["running"],
            "started": job["started"],
            "finished": job["finished"],
            "exitCode": job["exitCode"],
            "lines": list(job["lines"]),
            "zipPath": job["zipPath"],
            "zipSize": job["zipSize"],
            "error": job["error"],
            "chunkOnly": job.get("chunkOnly", False),
            "note": job.get("note", ""),
        }


def run_backup_job(job, cfg_path, save_path, chunk_only=False, note="", cleanup_path=None):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"
    flags = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW
    cmd = [sys.executable, "-u", str(BACKUP_RUNNER), str(cfg_path)]
    if chunk_only:
        cmd.append("--chunk-only")
    if note:
        cmd.append("--note=" + note)
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(PROJECT_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            env=env,
            creationflags=flags,
        )
        with BACKUP_LOCK:
            job["pid"] = proc.pid
        for line in proc.stdout:
            line = line.rstrip("\r\n")
            with BACKUP_LOCK:
                job["lines"].append(line)
                if len(job["lines"]) > 800:
                    del job["lines"][: len(job["lines"]) - 800]
        code = proc.wait()
        with BACKUP_LOCK:
            job["exitCode"] = code
            if code != 0:
                job["error"] = f"备份进程退出码 {code}"
    except Exception as e:
        with BACKUP_LOCK:
            job["error"] = str(e)
            job["lines"].append("无法启动备份：" + str(e))
            job["exitCode"] = -1
    finally:
        if cleanup_path:
            try:
                os.remove(cleanup_path)
            except OSError:
                pass
        zip_path = find_backup_zip(save_path, job["started"])
        with BACKUP_LOCK:
            job["zipPath"] = str(zip_path) if zip_path else None
            job["zipSize"] = zip_path.stat().st_size if zip_path else 0
            job["finished"] = time.time()
            job["running"] = False


def normalize_extra_partials(value):
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("extra_partials 必须是数组")
    items = []
    for item in value:
        if not isinstance(item, dict) or item.get("files") is not None:
            continue
        folder = item.get("folder")
        folders_ok = isinstance(folder, str) or (
            isinstance(folder, list) and all(isinstance(x, str) for x in folder)
        )
        if not folders_ok:
            continue
        if not all(key in item for key in ("x1", "z1", "x2", "z2")):
            continue
        items.append(item)
    return items


def start_backup(path=None, chunk_only=False, note="", extra_partials=None, config=None, name=None):
    global BACKUP_JOB
    note = note.strip()[:40] if isinstance(note, str) else ""
    if config is not None:
        cfg = validate_config(config)
        display_name = (name.strip()[:80] if isinstance(name, str) and name.strip() else "") or "浏览器配置"
        cfg_path = None
    else:
        cfg = read_config_file(path)
        display_name = path.name
        cfg_path = path
    save_path = cfg.get("save_path")
    if not isinstance(save_path, str) or not save_path.strip():
        raise ValueError("配置的 save_path 无效")
    save_path = Path(os.path.expanduser(save_path)).resolve()
    if not save_path.is_dir():
        raise ValueError("配置中的存档目录不存在")

    temp_cfg = None
    extras = normalize_extra_partials(extra_partials)
    if extras or config is not None:
        combined = dict(cfg)
        saved_partials = combined.get("partials")
        combined["partials"] = (saved_partials if isinstance(saved_partials, list) else []) + extras
        fd, temp_name = tempfile.mkstemp(prefix="mc-backup-", suffix=".json")
        os.close(fd)
        temp_cfg = Path(temp_name)
        temp_cfg.write_text(json.dumps(combined, ensure_ascii=False), encoding="utf-8")
        cfg_path = temp_cfg

    with BACKUP_LOCK:
        if BACKUP_JOB is not None and BACKUP_JOB["running"]:
            if temp_cfg is not None:
                try:
                    temp_cfg.unlink()
                except OSError:
                    pass
            raise RuntimeError("已有备份任务正在运行，请等它结束")
        job = {
            "id": time.strftime("%Y%m%d-%H%M%S") + "-" + os.urandom(2).hex(),
            "file": display_name,
            "running": True,
            "started": time.time(),
            "finished": None,
            "exitCode": None,
            "lines": [],
            "zipPath": None,
            "zipSize": 0,
            "error": None,
            "pid": None,
            "chunkOnly": bool(chunk_only),
            "note": note,
        }
        BACKUP_JOB = job
    threading.Thread(
        target=run_backup_job,
        args=(
            job,
            cfg_path,
            save_path,
            bool(chunk_only),
            note,
            str(temp_cfg) if temp_cfg is not None else None,
        ),
        daemon=True,
    ).start()
    return public_job(job)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "MCWorldMap/1.0"

    def log_message(self, fmt, *args):
        if VERBOSE:
            super().log_message(fmt, *args)

    def send_bytes(self, body, content_type, status=200, extra=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if extra:
            for k, v in extra.items():
                self.send_header(k, v)
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_bytes(body, "application/json; charset=utf-8", status)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)
        if path in ("/", "/index.html"):
            # 刷新/新标签会重新请求首页，撤销上一页面关闭上报带来的待关闭状态
            note_navigation()
        touch_page(qs.get("sid", [""])[0])
        try:
            parsed = urlparse(self.path)
            path = parsed.path
            if path == "/api/health":
                self.send_json({"ok": True})
                return
            if path == "/api/info":
                qs = parse_qs(parsed.query)
                wd = get_world()
                if qs.get("refresh", ["0"])[0] == "1" and wd is not None:
                    try:
                        wd = load_world(wd.info["path"], persist=False)
                    except ValueError as e:
                        self.send_json({"error": str(e)}, 400)
                        return
                if wd is None:
                    self.send_json({"world": None, "dimensions": []})
                else:
                    self.send_bytes(wd.json, "application/json; charset=utf-8")
                return
            if path == "/api/waypoints":
                wd = get_world()
                if wd is None:
                    self.send_json({"available": False, "worldDir": "", "dimensions": {}, "total": 0})
                else:
                    self.send_json(read_xaero_waypoints(wd))
                return
            if path == "/api/activity":
                qs = parse_qs(parsed.query)
                wd = get_world()
                if wd is None:
                    self.send_json({"error": "尚未加载存档"}, 400)
                    return
                dim_id = qs.get("dim", [""])[0]
                dim = next((d for d in wd.info["dimensions"] if d["id"] == dim_id), None)
                if dim is None:
                    self.send_json({"error": "维度不存在"}, 400)
                    return
                try:
                    min_seconds = float(qs.get("min", ["0"])[0])
                except ValueError:
                    min_seconds = 0
                min_seconds = min(max(min_seconds, 0), 365 * 86400)
                self.send_json(scan_dim_activity(wd, dim, min_seconds))
                return
            if path == "/api/tile":
                self.handle_tile(parse_qs(parsed.query))
                return
            if path == "/api/icon":
                self.handle_icon()
                return
            if path == "/api/configs":
                self.send_json({"dir": str(CONFIGS_DIR), "configs": list_configs()})
                return
            if path == "/api/entries":
                wd = get_world()
                if wd is None:
                    self.send_json({"error": "尚未加载存档"}, 400)
                    return
                self.send_json(list_save_entries(wd))
                return
            if path == "/api/backup/status":
                self.send_json({"job": public_job(BACKUP_JOB)})
                return
            self.handle_static(path)
        except Exception as e:
            if VERBOSE:
                import traceback
                traceback.print_exc()
            try:
                self.send_json({"error": str(e)}, 500)
            except Exception:
                pass

    def read_json_body(self):
        try:
            length = int(self.headers.get("Content-Length", "0") or 0)
        except ValueError:
            raise ValueError("请求长度无效")
        if length < 0 or length > 20 * 1024 * 1024:
            raise ValueError("请求体过大")
        body = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(body.decode("utf-8-sig"))
        except Exception:
            raise ValueError("请求不是有效的 JSON")
        if not isinstance(data, dict):
            raise ValueError("请求必须是 JSON 对象")
        return data

    def do_POST(self):
        try:
            parsed = urlparse(self.path)
            data = self.read_json_body()

            if parsed.path == "/api/shutdown":
                report_page_closed(data.get("sid") or "")
                self.send_json({"ok": True})
                return

            if parsed.path == "/api/pick-folder":
                raw = data.get("initial")
                initial = None
                if isinstance(raw, str) and raw.strip():
                    p = Path(os.path.expanduser(raw.strip().strip('"')))
                    if p.is_dir():
                        initial = p
                    elif p.parent.is_dir():
                        initial = p.parent
                if initial is None:
                    wd = get_world()
                    initial = Path(wd.info["path"]).parent if wd is not None else Path.home()
                self.send_json({"path": pick_folder_dialog(str(initial))})
                return

            if parsed.path == "/api/open-save-dir":
                wd = get_world()
                if wd is None:
                    raise ValueError("尚未加载存档")
                folder = Path(wd.info["path"])
                if not folder.is_dir():
                    raise ValueError("存档目录不存在")
                reveal_in_folder(folder)
                self.send_json({"ok": True, "path": str(folder)})
                return

            if parsed.path == "/api/backup/reveal":
                with BACKUP_LOCK:
                    zip_path = BACKUP_JOB.get("zipPath") if BACKUP_JOB else None
                if not zip_path:
                    raise ValueError("还没有可定位的备份文件")
                target = Path(zip_path)
                if not target.is_file():
                    raise ValueError("备份文件不存在")
                reveal_in_folder(target)
                self.send_json({"ok": True, "path": str(target)})
                return

            if parsed.path == "/api/world":
                path = data.get("path")
                if not isinstance(path, str) or not path.strip():
                    raise ValueError("请填写存档路径")
                wd = load_world(path)
                self.send_bytes(wd.json, "application/json; charset=utf-8")
                return

            if parsed.path == "/api/configs/load":
                path = config_path(data.get("file"), must_exist=True)
                try:
                    cfg = read_config_file(path)
                except json.JSONDecodeError as e:
                    raise ValueError(f"配置 JSON 格式错误：{e}")
                save_path = cfg.get("save_path")
                if not isinstance(save_path, str) or not save_path.strip():
                    raise ValueError("配置缺少有效的 save_path")
                try:
                    wd = load_world(save_path)
                except ValueError as e:
                    raise ValueError(f"配置中的存档无法加载：{e}")
                self.send_json({"file": path.name, "config": cfg, "world": wd.info})
                return

            if parsed.path == "/api/configs/save":
                path = config_path(data.get("file"))
                cfg = validate_config(data.get("config"))
                backup_name = save_config_file(path, cfg)
                self.send_json({"file": path.name, "path": str(path), "backupFile": backup_name})
                return

            if parsed.path == "/api/backup":
                if data.get("config") is not None:
                    job = start_backup(
                        chunk_only=bool(data.get("chunk_only")),
                        note=data.get("note") or "",
                        extra_partials=data.get("extra_partials"),
                        config=data.get("config"),
                        name=data.get("name"),
                    )
                else:
                    path = config_path(data.get("file"), must_exist=True)
                    job = start_backup(
                        path,
                        bool(data.get("chunk_only")),
                        data.get("note") or "",
                        data.get("extra_partials"),
                    )
                self.send_json({"job": job})
                return

            self.send_json({"error": "未知接口"}, 404)
        except ValueError as e:
            self.send_json({"error": str(e)}, 400)
        except RuntimeError as e:
            self.send_json({"error": str(e)}, 409)
        except Exception as e:
            if VERBOSE:
                import traceback
                traceback.print_exc()
            self.send_json({"error": str(e)}, 500)

    def handle_tile(self, qs):
        wd = get_world()
        if wd is None:
            self.send_json({"error": "尚未加载存档"}, 400)
            return
        dim_id = qs.get("dim", [""])[0]
        try:
            rx = int(qs.get("x", ["0"])[0])
            rz = int(qs.get("z", ["0"])[0])
            size = int(qs.get("res", ["512"])[0])
        except ValueError:
            self.send_json({"error": "坐标参数无效"}, 400)
            return
        if size not in (256, 512):
            size = 512
        try:
            gz = get_tile(wd, dim_id, rx, rz, size)
        except Exception as e:
            self.send_json({"error": f"渲染失败: {e}"}, 500)
            return
        if gz is None:
            self.send_json({"error": "该区域文件不存在"}, 404)
            return
        self.send_bytes(gz, "application/octet-stream", 200, {"Content-Encoding": "gzip"})

    def handle_icon(self):
        wd = get_world()
        if wd is None:
            self.send_json({"error": "尚未加载存档"}, 404)
            return
        icon = Path(wd.info["path"]) / "icon.png"
        try:
            body = icon.read_bytes()
        except OSError:
            self.send_json({"error": "没有图标"}, 404)
            return
        self.send_bytes(body, "image/png")

    def handle_static(self, path):
        files = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/index.html": ("index.html", "text/html; charset=utf-8"),
            "/offline.html": ("offline.html", "text/html; charset=utf-8"),
            "/app.js": ("app.js", "application/javascript; charset=utf-8"),
            "/style.css": ("style.css", "text/css; charset=utf-8"),
            "/manifest.webmanifest": ("manifest.webmanifest", "application/manifest+json; charset=utf-8"),
            "/sw.js": ("sw.js", "application/javascript; charset=utf-8"),
            "/icon.svg": ("icon.svg", "image/svg+xml"),
            "/icon-192.png": ("icon-192.png", "image/png"),
            "/icon-512.png": ("icon-512.png", "image/png"),
        }
        item = files.get(path)
        if item is None:
            if path == "/favicon.ico":
                self.send_bytes(b"", "image/x-icon", 204)
                return
            self.send_json({"error": "Not Found"}, 404)
            return
        file_path = PUBLIC_DIR / item[0]
        try:
            body = file_path.read_bytes()
        except OSError:
            self.send_json({"error": "缺少静态文件"}, 404)
            return
        self.send_bytes(body, item[1])


def find_port(start, strict=False):
    if strict:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", start))
                return start
            except OSError as e:
                reason = e.strerror or str(e)
                raise RuntimeError(
                    f"端口 {start} 不可用（{reason}）。"
                    f"\n请关闭占用该端口的程序，或加 --port 指定其它端口"
                )
    for port in range(start, start + 30):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"从 {start} 起连续 30 个端口都不可用")


PICK_LOCK = threading.Lock()


def pick_folder_dialog(initial=None):
    """打开系统文件夹选择框，返回所选目录；取消时返回空字符串。"""
    if sys.platform != "win32":
        raise RuntimeError("当前系统不支持系统文件夹选择框，请手动填写路径")
    if not PICK_LOCK.acquire(blocking=False):
        raise RuntimeError("已经有一个文件夹选择窗口打开了")
    root = None
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        kwargs = {
            "parent": root,
            "title": "选择包含 level.dat 的存档文件夹",
            "mustexist": True,
        }
        if initial:
            try:
                if Path(initial).is_dir():
                    kwargs["initialdir"] = str(initial)
            except OSError:
                pass
        return filedialog.askdirectory(**kwargs) or ""
    except Exception as e:
        raise RuntimeError(f"文件夹选择窗口打开失败：{e}")
    finally:
        if root is not None:
            try:
                root.destroy()
            except Exception:
                pass
        PICK_LOCK.release()


def reveal_in_folder(path):
    target = str(path)
    if sys.platform == "win32":
        subprocess.Popen(["explorer", "/select," + target])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-R", target])
    else:
        subprocess.Popen(["xdg-open", str(Path(target).parent)])


def init_worker():
    # Console Ctrl+C is delivered to every process in the group on Windows;
    # without this the idle pool workers print a KeyboardInterrupt traceback.
    try:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
    except (OSError, ValueError):
        pass

def launch_pwa_shortcut():
    lnk = BASE_DIR / "app.lnk"
    if not lnk.is_file():
        return False
    try:
        os.startfile(str(lnk))
        print(f"已通过快捷方式启动 PWA：{lnk.name}")
        return True
    except OSError as e:
        print(f"快捷方式启动失败：{e}")
        return False

def launch_app_window(url: str) -> bool:
    """跨平台尝试以应用窗口模式启动 URL。返回 True 表示已用特殊模式启动。"""
    exe_candidates = []
    if sys.platform == "win32":
        exe_candidates = [
            shutil.which("chrome"),
            shutil.which("msedge"),
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        ]
    elif sys.platform == "darwin":
        exe_candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        ]
    elif sys.platform.startswith("linux"):
        exe_candidates = [
            shutil.which("google-chrome"),
            shutil.which("microsoft-edge"),
            shutil.which("brave-browser"),
            shutil.which("chromium"),
        ]

    # 1) 优先 Chromium 系 --app
    for exe in exe_candidates:
        if exe and os.path.isfile(exe):
            try:
                subprocess.Popen([exe, f"--app={url}"])
                return True
            except OSError:
                continue

    # 2) 回退 Firefox -kiosk（全屏无UI，体验有限）
    firefox = shutil.which("firefox")
    if firefox:
        try:
            subprocess.Popen([firefox, "-kiosk", url])
            return True
        except OSError:
            pass

    # 3) 最终回退：普通浏览器标签页
    webbrowser.open(url)
    return False

_TRUE_VALS = {"1", "true", "yes", "on", ""}
_FALSE_VALS = {"0", "false", "no", "off"}


def normalize_argv(argv):
    """翻译 mcbackup:// 协议 URL 为命令行参数。

    规则：
      - mcbackup://start?<query>    → query 里每个 key 都变成 --key [value]
      - mcbackup://backend?<query>  → 同上，最后强制追加 --no-browser
      - 其它 argv 原样透传

    query 映射规则：
      ?port=8787        → --port 8787
      ?world=E:/saves   → --world E:/saves（值需 URL 编码，parse_qs 自动解码）
      ?verbose          → --verbose（无值视为开）
      ?verbose=1        → --verbose
      ?verbose=0        → 忽略（false 值不传）
    """
    out = []
    for arg in argv:
        if not arg.startswith("mcbackup://"):
            out.append(arg)
            continue

        parsed = urlparse(arg)
        action = parsed.netloc.lower()
        if action not in ("start", "backend"):
            continue  # 未知动作直接忽略

        qs = parse_qs(parsed.query, keep_blank_values=True)
        cli = []
        for key, vals in qs.items():
            if not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_-]*", key):
                continue
            val = vals[-1] if vals else ""
            low = val.lower()
            if low in _FALSE_VALS:
                continue
            if low in _TRUE_VALS:
                cli.append("--" + key)
            else:
                cli.extend(["--" + key, val])

        if action == "backend" and "--no-browser" not in cli:
            cli.append("--no-browser")

        out.extend(cli)
    return out

def main():
    global EXECUTOR, VERBOSE
    parser = argparse.ArgumentParser(description="MC存档选区备份工具")
    parser.add_argument("--world", help="存档目录")
    parser.add_argument("--port", type=int, default=None,
                    help=f"指定后仅使用该端口，占用则报错退出；不指定时从 {DEFAULT_PORT} 起自动寻找")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(normalize_argv(sys.argv[1:]))
    VERBOSE = args.verbose

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    workers = max(1, min(8, (os.cpu_count() or 4) - 1))
    EXECUTOR = concurrent.futures.ProcessPoolExecutor(
        max_workers=workers, initializer=init_worker
    )

    if args.world:
        try:
            load_world(args.world, persist=True)
        except ValueError as e:
            print(f"无法加载存档：{e}")

    threading.Thread(target=cleanup_cache, daemon=True).start()

    try:
        if args.port is not None:
            if not (0 < args.port < 65536):
                raise RuntimeError(f"端口 {args.port} 无效，需要在 1–65535 之间")
            port = find_port(args.port, strict=True)
        else:
            port = find_port(DEFAULT_PORT)
    except RuntimeError as e:
        EXECUTOR.shutdown(wait=False, cancel_futures=True)
        raise

    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    httpd.daemon_threads = True
    # 启动看门狗
    threading.Thread(target=shutdown_watcher, args=(httpd,), daemon=True).start()
    url = f"http://127.0.0.1:{port}/"
    print(f"MC存档选区备份工具已启动：{url}")
    # print(f"存档：{WORLD_DATA.info['path'] if WORLD_DATA else '尚未选择'}")
    if not args.no_browser:
        def open_app():
            if launch_pwa_shortcut():
                # 启动了 PWA 快捷方式，等 8 秒看是否有发心跳
                def verify():
                    time.sleep(8)
                    with SERVER_LOCK:
                        alive = len(ACTIVE_PAGES) > 0
                    if not alive:
                        print("PWA 未产生心跳，使用浏览器打开…")
                        launch_app_window(url)
                threading.Thread(target=verify, daemon=True).start()
            else:
                print("没有找到 app.lnk，自动打开浏览器…")
                launch_app_window(url)
            print("若未启动成功，请手动点击或复制上方URL打开浏览器使用")
            print("\n关闭网页本窗口自动关闭，或按 Ctrl+C 停止。")
        threading.Timer(0.1, open_app).start()
    print("\n按 Ctrl+C 停止。")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n正在安全退出…")
    finally:
        httpd.server_close()
        EXECUTOR.shutdown(wait=False, cancel_futures=True)
        print("已停止。")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        # Keep the window readable when launched by start_map.bat (cmd /c closes on exit).
        if VERBOSE:
            traceback.print_exc()
        else:
            print(f"{e}")
        print("\n启动失败")
        for sec in range(3, 0, -1):
            print(f"\r{sec} 秒后关闭窗口… ", end="", flush=True)
            time.sleep(1)
        print("\r窗口关闭中…" + " " * 20, flush=True)
        sys.exit(1)
