import json
import os
import shutil
import time
import zipfile
import tempfile
os.chdir(os.path.dirname(os.path.abspath(__file__))) #cr. Miranda_Meow
# 作者：Yinhe233，主要代码由ai生成

lang = 'EN'
prt = True

ticker = 0.0
errRpt = []
errRptIgnoreL = 0

def printer(cn, en, logErr=False):
    if lang == 'CN':
        print(cn)
        if logErr: errRpt.append(cn)
    else: 
        print(en)
        if logErr: errRpt.append(en)

def folder_warning(item): 
    printer(f'读取\n{item}\n时出错：必须声明folder或folders！将跳过此块。', f'An error happened when reading: \n{item}\nMust declare either folder or folders. Will skip this chunk.', True)

def xz_warning(item): 
    printer(f'读取\n{item}\n时出错：必须声明x1,x2,z1,z2。将跳过此块。', f'An error happened when reading: \n{item}\nMust declare x1, x2, z1 and z2. Will skip this chunk.', True)

def xz_list_warning(item): 
    printer(f'读取\n{item}\n时出错：x1,x2,z1,z2必须同时为数字或等长数组。将跳过此块。', f'An error happened when reading: \n{item}\nx1, x2, z1 and z2 must be all number or arries of equal length. Will skip this chunk.', True)

def path_warning(src):
    printer(f'路径{src}不存在，跳过。', f'Path {src} does not exist. Skipping.', True)

def hasNone(items): 
    for itm in items: 
        if itm is None: return True
    return False

def rl(arr): 
    return range(len(arr))

# --------------------------
# region 文件名生成函数
# --------------------------
def compile_regions(x1, z1, x2, z2):
    regions = []
    min_x = min(x1, x2) // 512
    max_x = max(x1, x2) // 512
    min_z = min(z1, z2) // 512
    max_z = max(z1, z2) // 512
    for x in range(min_x, max_x + 1):
        for z in range(min_z, max_z + 1):
            regions.append(f"r.{x}.{z}.mca")
    return regions

# --------------------------
# 从 JSON 读取配置
# --------------------------
def load_config(config_path="config.json"):
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    return cfg

def folder_getter(item): 
    if item.get('folder') != None: 
        return item["folder"]
    elif item.get('folders') != None: 
        return item['folders']
    folder_warning(item)
    return None

def build_path_unit_files_helper(folder, files, paths): 
    for f in files:
        p = os.path.join(folder, f).replace("\\", "/")
        paths.append(p)

def build_path_unit_files(folder, item, paths):
    files = item.get("files", [])
    if isinstance(folder, list): 
        for ff in folder: 
            build_path_unit_files_helper(ff, files, paths)
    else: 
        build_path_unit_files_helper(folder, files, paths)
            
def xz_legit_check(xzs): 
    l = 0
    lst = isinstance(xzs[0], list)
    if lst: l = len(xzs[0])
    for xz in xzs: 
        if isinstance(xz, list) != lst: 
            return False
        if lst and len(xz) != l: 
            return False
    return True

def build_path_unit_regions_helper(folder, regions, paths): 
    for r in regions:
        p = os.path.join(folder, r).replace("\\", "/")
        paths.append(p)

def build_path_unit_regions(folder, item, paths): 

    x1 = item.get('x1')
    z1 = item.get('z1')
    x2 = item.get('x2')
    z2 = item.get('z2')
    if hasNone([x1,x2,z1,z2]): 
        xz_warning(item)
        return
    if not xz_legit_check([x1,x2,z1,z2]): 
        xz_list_warning(item)
        return
    
    if not isinstance(x1, list): 
        regions = compile_regions(x1, z1, x2, z2)
        if isinstance(folder, list): 
            for fd in folder: 
                build_path_unit_regions_helper(fd, regions, paths)
        else:
            build_path_unit_regions_helper(folder, regions, paths)
        return

    for i in rl(x1): 
        regions = compile_regions(x1[i], z1[i], x2[i], z2[i])
        if isinstance(folder, list): 
            for fd in folder: 
                build_path_unit_regions_helper(fd, regions, paths)
        else:
            build_path_unit_regions_helper(folder, regions, paths)
    

# --------------------------
# 把 ignores / partials 展开为路径列表
# --------------------------
def build_paths(items):
    paths = []
    for item in items:
        # 直接路径字符串
        if isinstance(item, str):
            paths.append(item.replace("\\", "/"))
            continue

        # 文件夹+文件列表
        if isinstance(item, dict):
            folder = folder_getter(item)
            if folder == None: continue
            if item.get("files") != None: 
                build_path_unit_files(folder, item,paths)
            else: 
                build_path_unit_regions(folder, item,paths)

            
    return paths

# --------------------------
# 复制：忽略 ignores 列表
# --------------------------
def smart_copy(src, dst, ignores):
    if not os.path.exists(src):
        path_warning(src)
        return
    os.makedirs(dst, exist_ok=True)
    for root, dirs, files in os.walk(src, topdown=True):
        rel_path = os.path.relpath(root, src)
        dirs[:] = [d for d in dirs if not is_ignored(os.path.join(rel_path, d), ignores)]
        for file in files:
            file_rel = os.path.join(rel_path, file) if rel_path != "." else file
            if is_ignored(file_rel, ignores):
                continue
            src_file = os.path.join(root, file)
            if not os.path.exists(src_file): 
                path_warning(src_file)
                continue
            dst_file = os.path.join(dst, file_rel)
            os.makedirs(os.path.dirname(dst_file), exist_ok=True)
            shutil.copy2(src_file, dst_file)

def is_ignored(path, ignores):
    path = path.replace("\\", "/")
    for ig in ignores:
        ig = ig.replace("\\", "/")
        if path == ig or path.startswith(ig + "/"):
            return True
    return False

# --------------------------
# 按列表复制文件
# --------------------------
def copy_list(file_list, src_root, dst_root):
    for item in file_list:
        src = os.path.join(src_root, item)
        if not os.path.exists(src):
            continue
        if os.path.isdir(src): 
            smart_copy(src,dst_root,[])
            continue
        dst = os.path.join(dst_root, item)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)

# --------------------------
# 打包 ZIP
# --------------------------
def zip_folder(folder_path, output_zip):
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(folder_path):
            for file in files:
                full = os.path.join(root, file)
                rel = os.path.relpath(full, folder_path)
                zf.write(full, rel)

# --------------------------
# 主入口
# --------------------------
def main(config_path):
    cfg = load_config(config_path)
    save_path = cfg.get("save_path", "")
    ignores_raw = cfg.get("ignores", [])
    partials_raw = cfg.get("partials", [])

    printer(f"读取到存档路径：\n{save_path}", f"Save path loaded: {save_path}", True)
    global errRptIgnoreL
    errRptIgnoreL += 1

    if not save_path or not os.path.isdir(save_path):
        printer("存档路径无效或不存在", "Save path not found.", True)
        return
    
    printer("开始备份...", "Starting backup...")

    ignore_list = build_paths(ignores_raw)
    partial_list = build_paths(partials_raw)

    # 把 partial 所在目录加入忽略，避免重复复制
    for p in partial_list:
        d = os.path.dirname(p)
        if d and d not in ignore_list:
            ignore_list.append(d)

    if prt:
        printer("\n===== 忽略路径 =====", "\n===== ignores =====")
        for p in ignore_list:
            print(p)

    if prt:
        printer("\n===== 部分复制 =====", "\n===== partials =====")
        for p in partial_list:
            print(p)

    with tempfile.TemporaryDirectory() as temp_dir:
        if prt:
            printer("\n正在复制基础文件（排除忽略项）...","Copying all not ignored...")
        smart_copy(save_path, temp_dir, ignore_list)

        if prt:
            print("正在复制部分备份文件...", "Copying partials...")
        copy_list(partial_list, save_path, temp_dir)

        tmark = time.strftime("%Y-%m-%d_%H%M%S")
        zip_name = f"{save_path}_{tmark}_partial.zip"
        if prt:
            printer(f"正在打包：{zip_name}",f"Zipping up: {zip_name}")
        zip_folder(temp_dir, zip_name)

    printer(f"已完成打包{zip_name}", f"Zipping {zip_name} done.")
    tused = int(time.time() - ticker)
    printer(f"本次耗时{tused}秒", f"{tused} seconds used this time")

if __name__ == "__main__":
    glbcfg = load_config("global_config.json")
    lang = glbcfg.get("language")
    if lang == '中文' or lang == '中' or lang == '文': 
        lang = 'CN'
    else: 
        lang = 'EN'
    prt = glbcfg.get("print_full_process")
    configs = glbcfg.get('config_paths')
    ignore_errors = glbcfg.get('ignore_errors',False)
    for cc in configs: 
        ticker = time.time()
        if cc == 'can/also/do/relOrAbs/paths/to/someConfig.json' or os.path.basename(cc) == 'config_template.json': 
            continue
        if not os.path.exists(cc): 
            printer(f'指定位置{cc}不存在。请检查拼写。',f'{cc} doesn\'t exist. Please check your spelling.', True)
            continue
        # Single file
        if os.path.splitext(cc)[1] == '.json': 
            printer(f'\n开始执行{cc}配置指令',f'\nStart running with {cc}', True)
            errRptIgnoreL += 1
            main(cc.replace("\\", "/"))
            continue
        # Folder
        files = os.listdir(cc)
        for file in files: 
            if os.path.splitext(file)[1] != '.json' or file == 'config_template.json': 
                continue
            printer(f'\n开始执行{file}配置指令',f'\nStart running with {file}', True)
            errRptIgnoreL += 1
            main(os.path.join(cc,file).replace("\\", "/"))

    if len(errRpt) > errRptIgnoreL and not ignore_errors: 
        os.makedirs('errors', exist_ok=True)
        tmark = time.strftime("%Y-%m-%d_%H%M%S")
        thisReport = f"error_report_{tmark}.txt"
        with open(os.path.join('errors', thisReport), "w", encoding="utf-8") as f: 
            f.write('\n'.join(map(str,errRpt)))

    printer('备份完成！','Backup complete!')