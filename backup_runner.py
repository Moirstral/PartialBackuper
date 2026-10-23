import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

import script

SECTOR = 4096
HEADER = 8192
CHUNK = 16
INVALID_FILENAME_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')


def safe_note(note):
    text = INVALID_FILENAME_RE.sub("_", str(note or "")).strip()
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text[:40].strip(" .")


def log(cn, en, err=False):
    script.printer(cn, en, err)


def load_global():
    glb = {}
    try:
        glb = json.loads((ROOT / "global_config.json").read_text(encoding="utf-8-sig"))
    except Exception:
        pass
    lang = glb.get("language")
    script.lang = "CN" if lang in ("中文", "中", "文") else "EN"
    script.prt = bool(glb.get("print_full_process", True))
    script.ticker = time.time()
    return glb


def norm_folder(folder):
    value = str(folder).replace("\\", "/").strip()
    return value.strip("/") or "."


def item_folders(item):
    if not isinstance(item, dict):
        return []
    folder = item.get("folder")
    if folder is None:
        folder = item.get("folders")
    if isinstance(folder, str):
        return [norm_folder(folder)] if folder.strip() else []
    if isinstance(folder, list):
        return [norm_folder(f) for f in folder if isinstance(f, str) and f.strip()]
    return []


def to_rect(values):
    try:
        x1, z1, x2, z2 = (int(v) for v in values)
    except (TypeError, ValueError):
        return None
    return (min(x1, x2), min(z1, z2), max(x1, x2), max(z1, z2))


def item_ranges(item):
    if not isinstance(item, dict) or item.get("files") is not None:
        return []
    x1 = item.get("x1")
    z1 = item.get("z1")
    x2 = item.get("x2")
    z2 = item.get("z2")
    if script.hasNone([x1, x2, z1, z2]):
        script.xz_warning(item)
        return []
    if not script.xz_legit_check([x1, x2, z1, z2]):
        script.xz_list_warning(item)
        return []
    if not isinstance(x1, list):
        rect = to_rect([x1, z1, x2, z2])
        if rect is None:
            script.xz_warning(item)
            return []
        return [rect]
    rects = []
    for values in zip(x1, z1, x2, z2):
        rect = to_rect(values)
        if rect is None:
            script.xz_warning(item)
            return []
        rects.append(rect)
    return rects


def collect_copy_paths(partials):
    paths = []
    for item in partials:
        if isinstance(item, str):
            paths.append(item.replace("\\", "/"))
            continue
        if not isinstance(item, dict) or item.get("files") is None:
            continue
        folder = script.folder_getter(item)
        if folder is None:
            continue
        script.build_path_unit_files(folder, item, paths)
    return paths


def add_range(regions, rect):
    x1, z1, x2, z2 = rect
    cx0 = x1 // CHUNK
    cx1 = x2 // CHUNK
    cz0 = z1 // CHUNK
    cz1 = z2 // CHUNK
    for rx in range(cx0 // 32, cx1 // 32 + 1):
        for rz in range(cz0 // 32, cz1 // 32 + 1):
            lx0 = max(cx0, rx * 32) - rx * 32
            lx1 = min(cx1, rx * 32 + 31) - rx * 32
            lz0 = max(cz0, rz * 32) - rz * 32
            lz1 = min(cz1, rz * 32 + 31) - rz * 32
            row = ((1 << (lx1 - lx0 + 1)) - 1) << lx0
            mask = regions.get((rx, rz), 0)
            for lz in range(lz0, lz1 + 1):
                mask |= row << (lz * 32)
            regions[(rx, rz)] = mask


def collect_chunk_selection(partials):
    by_folder = {}
    rect_count = 0
    for item in partials:
        if not isinstance(item, dict) or item.get("files") is not None:
            continue
        folders = item_folders(item)
        if not folders:
            continue
        rects = item_ranges(item)
        if not rects:
            continue
        for folder in folders:
            regions = by_folder.setdefault(folder, {})
            for rect in rects:
                add_range(regions, rect)
                rect_count += 1
    return by_folder, rect_count


def safe_under(root, rel):
    rel_path = Path(rel)
    if rel_path.is_absolute():
        raise ValueError(f"路径必须是相对路径：{rel}")
    target = (root / rel_path).resolve()
    root_path = Path(root).resolve()
    if target != root_path and root_path not in target.parents:
        raise ValueError(f"路径超出存档范围：{rel}")
    return target


def copy_region_chunks(src, dst, bits, rx, rz, src_dir, dst_dir):
    try:
        data = src.read_bytes()
    except OSError as e:
        log(f"读取区域文件失败，跳过：{src}（{e}）", f"Cannot read {src}: {e}", True)
        return 0
    if len(data) < HEADER:
        log(f"区域文件过小，跳过：{src}", f"Region file too small: {src}", True)
        return 0

    entries = []
    mcc_chunks = []
    for idx in range(1024):
        if not (bits >> idx) & 1:
            continue
        base = idx * 4
        offset = (data[base] << 16) | (data[base + 1] << 8) | data[base + 2]
        sectors = data[base + 3]
        if not offset or not sectors:
            continue
        pos = offset * SECTOR
        if pos + 5 > len(data):
            continue
        length = int.from_bytes(data[pos:pos + 4], "big")
        if length < 1 or pos + 4 + length > len(data):
            continue
        payload = data[pos + 4:pos + 4 + length]
        timestamp = data[4096 + base:4096 + base + 4]
        entries.append((idx, payload, timestamp))
        if payload and payload[0] == 128:
            mcc_chunks.append((rx * 32 + (idx % 32), rz * 32 + (idx // 32)))

    if not entries:
        return 0

    out = bytearray(HEADER)
    sector = 2
    kept = 0
    for idx, payload, timestamp in entries:
        need = (4 + len(payload) + SECTOR - 1) // SECTOR
        if need > 255:
            log(f"区块 {idx} 超出 region 单区块上限，跳过", f"Chunk {idx} is too large, skipped", True)
            continue
        base = idx * 4
        out[base] = (sector >> 16) & 0xFF
        out[base + 1] = (sector >> 8) & 0xFF
        out[base + 2] = sector & 0xFF
        out[base + 3] = need
        out[4096 + base:4096 + base + 4] = timestamp
        out.extend(len(payload).to_bytes(4, "big"))
        out.extend(payload)
        pad = need * SECTOR - 4 - len(payload)
        if pad:
            out.extend(b"\x00" * pad)
        sector += need
        kept += 1

    if not kept:
        return 0
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(out)

    for cx, cz in mcc_chunks:
        name = f"c.{cx}.{cz}.mcc"
        src_mcc = src_dir / name
        if src_mcc.is_file():
            try:
                dst_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_mcc, dst_dir / name)
            except OSError as e:
                log(f"复制外部区块失败：{name}（{e}）", f"Cannot copy external chunk {name}: {e}", True)
        else:
            log(f"外部区块文件缺失：{name}", f"External chunk missing: {name}", True)
    return kept


def write_chunk_backup(by_folder, save_path, temp_dir):
    total_chunks = 0
    total_regions = 0
    missing_regions = 0
    for folder, regions in by_folder.items():
        src_dir = safe_under(save_path, folder)
        dst_dir = safe_under(temp_dir, folder)
        for (rx, rz), bits in sorted(regions.items()):
            src = src_dir / f"r.{rx}.{rz}.mca"
            if not src.is_file():
                missing_regions += 1
                continue
            count = copy_region_chunks(
                src, dst_dir / src.name, bits, rx, rz, src_dir, dst_dir
            )
            if count:
                total_chunks += count
                total_regions += 1
    if missing_regions:
        log(
            f"{missing_regions} 个选区区域文件尚未生成，已跳过",
            f"{missing_regions} selected region file(s) do not exist and were skipped",
        )
    return total_chunks, total_regions


def region_coords(path):
    try:
        _, x, z = path.stem.split(".")
        return int(x), int(z)
    except (ValueError, AttributeError):
        return None


def copy_external_chunks(src, dst_dir):
    coords = region_coords(src)
    if coords is None:
        return 0, 0
    rx, rz = coords
    copied = 0
    missing = 0
    try:
        with open(src, "rb") as fh:
            head = fh.read(HEADER)
            if len(head) < HEADER:
                return 0, 0
            for idx in range(1024):
                base = idx * 4
                offset = (head[base] << 16) | (head[base + 1] << 8) | head[base + 2]
                sectors = head[base + 3]
                if not offset or not sectors:
                    continue
                fh.seek(offset * SECTOR)
                prefix = fh.read(5)
                if len(prefix) < 5 or prefix[4] != 128:
                    continue
                cx = rx * 32 + (idx % 32)
                cz = rz * 32 + (idx // 32)
                name = f"c.{cx}.{cz}.mcc"
                src_mcc = src.parent / name
                if not src_mcc.is_file():
                    missing += 1
                    continue
                try:
                    dst_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_mcc, dst_dir / name)
                    copied += 1
                except OSError as e:
                    log(f"复制外部区块失败：{name}（{e}）", f"Cannot copy external chunk {name}: {e}", True)
    except OSError as e:
        log(f"读取区域文件失败：{src}（{e}）", f"Cannot read {src}: {e}", True)
    return copied, missing


def copy_full_regions(partial_paths, save_path, temp_dir):
    copied = 0
    missing = 0
    mcc_copied = 0
    mcc_missing = 0
    seen = set()
    for rel in partial_paths:
        key = rel.replace("\\", "/").lower()
        if key in seen:
            continue
        seen.add(key)
        src = safe_under(save_path, rel)
        if not src.is_file():
            if rel.lower().endswith(".mca"):
                missing += 1
            continue
        dst = safe_under(temp_dir, rel)
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        except OSError as e:
            log(f"复制失败：{rel}（{e}）", f"Cannot copy {rel}: {e}", True)
            continue
        copied += 1
        if src.suffix.lower() == ".mca":
            found, lost = copy_external_chunks(src, dst.parent)
            mcc_copied += found
            mcc_missing += lost
    if missing:
        log(
            f"{missing} 个选区区域文件尚未生成，已跳过",
            f"{missing} selected region file(s) do not exist and were skipped",
        )
    if mcc_copied:
        log(
            f"已一并复制 {mcc_copied} 个外部区块文件（.mcc）",
            f"Copied {mcc_copied} external chunk file(s) (.mcc)",
        )
    if mcc_missing:
        log(
            f"{mcc_missing} 个外部区块文件缺失，已跳过",
            f"{mcc_missing} external chunk file(s) are missing and were skipped",
            True,
        )
    return copied


def run(config_path, chunk_only=False, note=""):
    cfg = script.load_config(str(config_path))
    save_path_str = cfg.get("save_path", "")
    ignores_raw = cfg.get("ignores", [])
    partials_raw = cfg.get("partials", [])

    log(f"读取到存档路径：\n{save_path_str}", f"Save path loaded: {save_path_str}", True)
    if not save_path_str or not os.path.isdir(save_path_str):
        log("存档路径无效或不存在", "Save path not found.", True)
        return 1

    save_path = Path(save_path_str).resolve()
    if chunk_only:
        log(
            "开始备份（仅保存选中区块，会重建区域文件）...",
            "Starting chunk-only backup (region files will be rebuilt)...",
        )
    else:
        log(
            "开始备份（保留完整区域文件）...",
            "Starting backup with full region files...",
        )

    ignore_list = script.build_paths(ignores_raw)
    partial_paths = script.build_paths(partials_raw)
    for p in partial_paths:
        d = os.path.dirname(p)
        if d and d not in ignore_list:
            ignore_list.append(d)

    copy_paths = collect_copy_paths(partials_raw)
    if chunk_only:
        by_folder, rect_count = collect_chunk_selection(partials_raw)
    else:
        by_folder, rect_count = {}, 0

    if script.prt:
        log("\n===== 忽略路径 =====", "\n===== ignores =====")
        for p in ignore_list:
            print(p)
        if chunk_only:
            log("\n===== 按区块写入选区 =====", "\n===== chunk selections =====")
            for folder, regions in sorted(by_folder.items()):
                print(f"{folder}: {len(regions)} regions")
            if copy_paths:
                log("\n===== 整体复制 =====", "\n===== full copies =====")
                for p in copy_paths:
                    print(p)
        else:
            log("\n===== 完整复制的区域文件 =====", "\n===== full region files =====")
            for p in partial_paths:
                print(p)

    with tempfile.TemporaryDirectory() as temp_dir:
        log("正在复制基础文件（排除忽略项）...", "Copying all not ignored...")
        script.smart_copy(str(save_path), temp_dir, ignore_list)

        if chunk_only:
            if copy_paths:
                log("正在复制配置中指定的完整文件...", "Copying files listed for full copy...")
                script.copy_list(copy_paths, str(save_path), temp_dir)

            if by_folder:
                log(
                    f"正在从 {rect_count} 个选区矩形中提取区块...",
                    f"Extracting chunks from {rect_count} selection rectangle(s)...",
                )
                chunks, regions = write_chunk_backup(by_folder, save_path, temp_dir)
                log(
                    f"已写入 {chunks} 个区块到 {regions} 个区域文件",
                    f"Wrote {chunks} chunk(s) into {regions} region file(s)",
                )
                if chunks == 0:
                    log(
                        "选区中没有找到已生成的区块，生成的压缩包只包含非区域文件",
                        "No generated chunks were found in the selection; the zip only has non-region files",
                        True,
                    )
        else:
            log(
                "正在复制选区涉及的完整区域文件...",
                "Copying full region files touched by the selection...",
            )
            copied = copy_full_regions(partial_paths, save_path, temp_dir)
            log(
                f"已复制 {copied} 个文件（含完整区域文件）",
                f"Copied {copied} file(s), including full region files",
            )

        tmark = time.strftime("%Y-%m-%d_%H%M%S")
        note = safe_note(note)
        note_part = f"_{note}" if note else ""
        zip_name = f"{save_path.as_posix()}{note_part}_{tmark}_partial.zip"
        log(f"正在打包：{zip_name}", f"Zipping up: {zip_name}")
        script.zip_folder(temp_dir, zip_name)

    log(f"已完成打包{zip_name}", f"Zipping {zip_name} done.")
    used = int(time.time() - script.ticker)
    log(f"本次耗时{used}秒", f"{used} seconds used this time")
    return 0


def main():
    parser = argparse.ArgumentParser(description="PartialBackuper backup runner")
    parser.add_argument("config")
    parser.add_argument("--chunk-only", action="store_true")
    parser.add_argument("--note", default="", help="optional note inserted into the zip filename")
    args = parser.parse_args()
    cfg_path = Path(args.config)
    if not cfg_path.is_file():
        print(f"配置文件不存在：{cfg_path}")
        return 2

    load_global()
    try:
        return run(cfg_path, args.chunk_only, args.note)
    except Exception as e:
        log(f"备份失败：{e}", f"Backup failed: {e}", True)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
