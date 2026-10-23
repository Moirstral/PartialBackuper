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


def build_world(path_str):
    p = Path(os.path.expanduser(path_str.strip().strip('"').strip("'"))).resolve()
    if not p.is_dir():
        raise ValueError("文件夹不存在")
    level_file = p / "level.dat"
    if not level_file.is_file():
        raise ValueError("不是有效的存档目录（缺少 level.dat）")

    name = p.name
    version = ""
    data_version = None
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
    cfg = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(cfg, dict):
        raise ValueError("配置必须是 JSON 对象")
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


def start_backup(path, chunk_only=False, note="", extra_partials=None):
    global BACKUP_JOB
    note = note.strip()[:40] if isinstance(note, str) else ""
    cfg = read_config_file(path)
    save_path = cfg.get("save_path")
    if not isinstance(save_path, str) or not save_path.strip():
        raise ValueError("配置的 save_path 无效")
    save_path = Path(os.path.expanduser(save_path)).resolve()
    if not save_path.is_dir():
        raise ValueError("配置中的存档目录不存在")

    cfg_path = path
    temp_cfg = None
    extras = normalize_extra_partials(extra_partials)
    if extras:
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
            "file": path.name,
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
            "/app.js": ("app.js", "application/javascript; charset=utf-8"),
            "/style.css": ("style.css", "text/css; charset=utf-8"),
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


def find_port(start):
    for port in range(start, start + 30):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("找不到可用端口")


def init_worker():
    # Console Ctrl+C is delivered to every process in the group on Windows;
    # without this the idle pool workers print a KeyboardInterrupt traceback.
    try:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
    except (OSError, ValueError):
        pass


def main():
    global EXECUTOR, VERBOSE
    parser = argparse.ArgumentParser(description="MC存档选区备份工具")
    parser.add_argument("--world", help="存档目录")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
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

    port = find_port(args.port)
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    httpd.daemon_threads = True
    url = f"http://127.0.0.1:{port}/"
    print(f"MC存档选区备份工具已启动：{url}")
    # print(f"存档：{WORLD_DATA.info['path'] if WORLD_DATA else '尚未选择'}")
    print("按 Ctrl+C 停止。")
    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
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
    except Exception:
        # Keep the window readable when launched by start_map.bat (cmd /c closes on exit).
        traceback.print_exc()
        try:
            input("\n启动失败，按回车键退出…")
        except (EOFError, OSError):
            pass
        sys.exit(1)
