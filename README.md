# PartialBackuper · Minecraft 存档选区备份工具

对 Minecraft 存档做**部分/选区备份**：只备份你关心的区域（区块级裁剪），而不是整个存档。
提供两种用法——**图形化桌面工具**（推荐）和**配置文件驱动的命令行备份**。
桌面工具是一个独立窗口（内嵌系统 WebView2），双击即开，程序内部自带本地服务，不需要浏览器、不需要装 PWA。

> 本仓库是 [Yinhe2332767/PartialBackuper](https://github.com/Yinhe2332767/PartialBackuper) 的 fork，
> 在原命令行工具之上新增了 `map_selector/` 桌面选区工具。许可与来源声明见文末与 [`NOTICE`](./NOTICE)。
>
> **这个分支（`desktop-webview`）是桌面版**；用浏览器 / PWA 打开的网页版仍在 `main` 分支上。

> **文档说明**：本 README 由 [Qoder](https://qoder.com) 生成，并随功能改动持续更新；内容以实际运行验证为准，
> 如与程序行为不一致，请以代码为准。

---

## 界面预览

![桌面工具窗口：左侧是存档信息、维度与选区列表，右侧是按区域渲染的地图](./screenshot.png)

左侧依次是存档概况（维度 / 区域 / 数据量）、维度切换、选区列表（含「活跃区块」）与配置文件、排除项；
右侧地图按区域文件渲染地形，可框选区块、悬停查看区块活动时长、显示 Xaero 路径点，选好后可直接备份。

---

## 环境要求

- **直接用 exe**：解压后双击即可，不需要安装 Python。
- **源码运行**：需要 **Python 3.8–3.12** 与 `pip install -r requirements.txt`（桌面窗口用 `pywebview`，
  它依赖的 `pythonnet` 目前没有更新版本的预编译包）。命令行备份部分仍然只用 Python 标准库。
- **Windows 10/11** 一般已自带 WebView2 运行时（Edge 内核）；缺失时程序会提示，安装
  [WebView2 Runtime](https://developer.microsoft.com/microsoft/downloads/?product=webview2) 即可。
- 本地服务只监听 `127.0.0.1`，不对外网开放，也不会真的被浏览器访问到。

---

## 快速开始

### 方式 A：桌面工具（推荐，图形化框选）

1. **打开程序**，两种来源任选其一：
   - **打包好的 exe**：双击 `dist\PartialBackuper\PartialBackuper.exe`（自己打包见下方「打包 exe」）。
   - **源码直跑**：双击根目录的 [`start_map.bat`](./start_map.bat)
     （或 [`map_selector/start_map.bat`](./map_selector/start_map.bat)，二者等价），需要 Python 3.8–3.12
     和 `pip install -r requirements.txt`。
   出现的就是一个独立窗口（内嵌系统 WebView2），本地服务在窗口内部自己起，
   **不需要浏览器、不需要装 PWA、不需要注册协议**。
2. **首次启动会让你选数据存放位置**（只问一次，之后自动沿用）：
   - **便携**：在程序旁边建 `UserData\`，把整个文件夹拷走就带走全部数据；
   - **系统目录**：`%APPDATA%\PartialBackuper`，重装或替换程序也不会丢数据。

   数据目录里放地图瓦片缓存、上次打开的存档记录、备份配置，以及窗口内的本地存储
   （「仅浏览器配置」和红叉排除标记都存在这里）。想重新选择，启动时加 `--choose`。
3. 在窗口里点 **直接打开存档**，再点 **浏览…** 从系统窗口选择存档文件夹（也可直接粘贴路径）
   → 自动按存档路径匹配已有配置：命中就加载该配置；没命中会新建一份**仅浏览器配置**
   （只存在本机的窗口本地存储里，关窗不会丢失，也不会弹“未保存”提示）
   → 在地图上**框选**要备份的区域（可细化到区块）
   → 需要落盘时在左侧「配置文件」点 **保存**（会自动存为 `实例名_存档名.json`，例如 `养老生存_一辈子的生存档.json`；
   存档不在实例目录（`saves` 的上一级）下时，只用存档名）。**只有手动点保存才会写入配置文件**，
   直接点备份不会把浏览器配置落盘，备份时用的是窗口里当前的配置内容
   → 点击**备份**。裁剪与打包由程序内部的 `backup_runner` 完成（打包版走 exe 自带的备份模式，不需要额外的 Python）。
4. 下次使用时，在「配置文件」的下拉框里**选中已有配置即切换**，无需再点加载，存档和选区会自动恢复；
   下拉框会同时列出磁盘配置和**所有仅浏览器配置**（后缀「· 仅浏览器」），
   选中浏览器配置会直接打开它对应的存档，重新打开程序也会自动回到上次的浏览器配置；
   若当前是本地配置且有未保存的修改，会先问是否保存。之后的改动点 **保存** 会直接写回当前配置
   （同名文件已存在时也是直接覆盖，原文件会自动留一份 `.bak`）。

> 窗口里跑的还是网页，同样拿不到拖入文件夹的完整路径，所以不能把存档文件夹直接拖进来打开；
> 请用 **浏览…** 选择。

> **右键框选删除区块**：放大到 **80%** 以上后，右键单击删除一个区块，**按住右键拖拽框选，松开后删除框内的区块**；
> 该操作**只作用于当前选区**（选区卡片上标有「当前」），不会影响其他选区；活跃选区没有设为当前时也不会被改动。删除后可以点「撤销」整批恢复。
> 在活动选区里右键改为**标记可抛弃**：区块正中间会显示红叉并留在选区里，再次右键即可恢复；标记只在备份时排除，重新扫描也不会丢失。
> 首次右键会弹出一次操作说明，之后可以点地图右上角的 **?** 重新查看。
>
> 桌面窗口没有浏览器工具栏，也不会执行 Edge 的鼠标手势，右键拖拽只用于框选区块。

**关闭与退出**

- 直接点窗口右上角关闭即可：本地服务和渲染用的后台进程一起退出，不会留下常驻服务。
- 如果备份还在进行，会先弹出确认框；选「继续备份」就回到窗口，选「退出」会中断本次备份。
- 启动失败时会弹出错误提示（加 `--verbose` 能看到调试输出）。

**命令行参数**（源码运行加在 `python desktop.py` 后面；exe 直接把参数追加在双击的目标之后，或写进快捷方式的“目标”里）：

| 参数 | 说明 |
| --- | --- |
| `--world <存档目录>` | 启动即加载该存档（路径会记到数据目录的 `world.json`） |
| `--port <端口>` | **固定端口**：指定后只使用该端口，被占用则报错退出；**不指定**时从 `8787` 起自动寻找可用端口 |
| `--data-dir <目录>` | 直接使用指定数据目录，不弹首次选择 |
| `--choose` | 重新选择数据存放位置（便携 / 系统目录） |
| `--verbose` | 打开调试输出与内嵌窗口的开发者工具 |

手动启动（等价于 `.bat` 做的事）：

```bash
cd map_selector
python desktop.py         # 可选：--world "路径" --port 8787 --data-dir "目录" --choose --verbose
```

### 打包 exe

1. 准备一个 **Python 3.8–3.12** 环境（桌面窗口的依赖只支持这几个版本）：

   ```bash
   pip install -r requirements.txt
   pip install pyinstaller
   ```

2. 双击或运行根目录的 [`build_exe.bat`](./build_exe.bat)（配置见 [`PartialBackuper.spec`](./PartialBackuper.spec)）。
3. 产物在 `dist\PartialBackuper\`，入口是 `dist\PartialBackuper\PartialBackuper.exe`。
   这是 **onedir 文件夹**形态，不是单文件：拷走时要连整个 `PartialBackuper` 文件夹一起复制。
4. 首次运行会询问数据目录；选「便携」就在 exe 旁边生成 `UserData\`。

> 打包版保存的备份配置默认写到**数据目录下的 `configs\`**；源码运行仍然读写仓库里的 `configs\`，
> 命令行备份（方式 B）不受影响。

### 方式 B：配置文件驱动的命令行备份（原始用法）

1. 进入 [`configs/`](./configs)，为**每个**要备份的存档复制一份
   [`config_template.json`](./configs/config_template.json) 并按说明填写
   （字段含义与示例见 [`configs/README_config.txt`](./configs/README_config.txt)）。
2. **双击 [`run_script.bat`](./run_script.bat)**（等价于 `python script.py`）。
3. 备份 zip 会生成在**每个存档所在的相同路径**下。
4. 若要读取 `configs/` 以外位置的配置，在 [`global_config.json`](./global_config.json) 的 `config_paths` 中注册（填目录则把其下每个 `.json` 当作一份配置，忽略子目录）。

---

## 恢复备份

- 若可以接受“未备份的部分继续存在”：直接解压备份，把文件复制回原存档、覆盖所有同名文件即可。
- 若不能接受（例如替换后仍无法进入存档）：在合理配置下，解压出来的备份本身即可当作一个完整存档直接使用。

> ⚠️ **务必检查路径拼写。** 脚本不含任何纠错功能。

---

## 卸载

双击根目录的 [`uninstall.bat`](./uninstall.bat)，按提示输入 `yes` 确认即可。它会：

- 删除程序文件（桌面入口、后端、前端界面、启动与打包脚本、说明文档）和打包产物 `dist/`、`build/`；
- 不写、也不清理任何注册表项或浏览器策略（本分支已经不用 `mcbackup://` 协议了）；
- 保留你的数据：`configs/`、`global_config.json`、数据目录（`UserData\` 或 `%APPDATA%\PartialBackuper`，
  里面有瓦片缓存、备份配置和窗口本地存储），以及各存档目录里的备份 zip。

卸载结束后会列出保留的内容和位置，如不再需要可自行删除；想彻底清除时直接删除整个文件夹即可。
若你选过「系统目录」，`%APPDATA%\PartialBackuper` 不会被脚本删掉，需要时手动删除。

> `.git` 目录（如果存在）和用户自己放入的其它文件不会被删除。若提示部分文件未能删除，
> 关闭程序窗口后重新运行脚本即可（此时脚本会保留以便重试）。

---

## 目录结构

```
.
├─ start_map.bat            # 桌面工具的根目录入口（源码运行时双击）
├─ build_exe.bat            # 打包：用 PyInstaller 生成 dist\PartialBackuper\
├─ PartialBackuper.spec     # PyInstaller 打包配置（onedir、无控制台窗口）
├─ run_script.bat           # 命令行备份入口（python script.py）
├─ uninstall.bat            # 卸载：删除程序文件，保留配置与数据目录
├─ script.py                # 原始命令行备份调度
├─ backup_runner.py         # 实际执行裁剪/打包（桌面工具的“备份”按钮也调用它）
├─ global_config.json       # 语言、config 读取路径等全局设置
├─ requirements.txt         # 桌面窗口的依赖（pywebview / pythonnet；命令行备份只用标准库）
├─ screenshot.png           # 界面预览图（文档用）
├─ configs/                 # 备份配置（内含模板与说明；个人配置默认不纳入版本控制）
├─ dist/                    # 打包产物（本机生成，不入库）
└─ map_selector/            # 桌面工具本体
   ├─ start_map.bat         # 本工具的启动入口（调 desktop.py）
   ├─ desktop.py            # 桌面入口：数据目录选择 → 起后端 → 开内嵌窗口
   ├─ server.py             # 本地 HTTP 服务 + 瓦片/活动/配置/备份接口
   ├─ renderer.py           # MCA/NBT 解析与地图渲染
   ├─ world.json            # 上次打开的存档（源码直跑时生成，不入库）
   └─ public/               # 前端（原生 JS，无构建步骤，由内嵌 WebView 加载）
      ├─ index.html
      ├─ app.js             # 界面、框选、备份流程
      ├─ style.css
      └─ icon.svg / icon-192.png / icon-512.png
```

---

## 关于依赖 / `requirements.txt`

- **命令行备份**（`script.py`、`backup_runner.py`）只用 **Python 标准库**，不需要安装任何第三方包。
- **桌面窗口**需要 `pywebview`（Windows 上依赖 `pythonnet`），因此源码运行要执行
  `pip install -r requirements.txt`；`pyinstaller` 只在打包时需要。
- 这两个包只提供最新的 Python 3.8–3.12 版本预编译文件，请用其中之一创建环境；
  用打包好的 exe 则完全不需要安装 Python。

---

## 许可与来源声明

- 本 fork 中对**新增/重写**的代码（主要是 `map_selector/` 桌面工具与启动、打包脚本）采用 **GNU AGPL-3.0**，见 [`LICENSE`](./LICENSE) 与 [`NOTICE`](./NOTICE)。采用 AGPL 的意图是：本作品保持自由，且不以闭源形式被商用；通过网络提供该服务时也须开放源码。
- **上游 [`Yinhe2332767/PartialBackuper`](https://github.com/Yinhe2332767/PartialBackuper) 目前没有许可证**（法律上默认“保留所有权利”）。因此：
  1. 若原作者提出要求，本仓库将下线（设为私有或删除）。
  2. 若上游日后为其代码补充许可证，本 fork 将针对继承而来的代码相应调整本仓库的许可条款。
- `script.py`、`backup_runner.py`、`global_config.json`、`requirements.txt`、`run_script.bat`、`configs/` 模板与说明等继承文件的著作权归原作者。

## 致谢

原作者 **Yinhe233**（原仓库说明：“作者：Yinhe233，主要代码由 AI 生成”）。
