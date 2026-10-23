# PartialBackuper · Minecraft 存档选区备份工具

对 Minecraft 存档做**部分/选区备份**：只备份你关心的区域（区块级裁剪），而不是整个存档。
提供两种用法——**图形化网页框选工具**（推荐）和**配置文件驱动的命令行备份**。

> 本仓库是 [Yinhe2332767/PartialBackuper](https://github.com/Yinhe2332767/PartialBackuper) 的 fork，
> 在原命令行工具之上新增了 `map_selector/` 网页选区工具。许可与来源声明见文末与 [`NOTICE`](./NOTICE)。

---

## 环境要求

- **Python 3**（仅需标准库，**无需 `pip install` 任何第三方包**；`http.server`、`pathlib`、`gzip`、`struct` 等自 3.7 起可用。开发与测试环境为 Python 3.15）。
- 提供 `.bat` 双击入口，面向 **Windows**；其他系统直接用 `python <脚本>` 运行。

---

## 快速开始

### 方式 A：网页选区工具（推荐，图形化框选）

1. **双击仓库根目录的 [`start_map.bat`](./start_map.bat)**（或 [`map_selector/start_map.bat`](./map_selector/start_map.bat)，二者等价）。
2. 服务会在自己的控制台窗口里启动，并自动用浏览器打开
   <http://127.0.0.1:8787/> 。
   若 `8787` 被占用，会自动向后查找可用端口（`8787`–`8816`）。
3. 在页面里选择 / 确认存档目录 → 在地图上**框选**要备份的区域（可细化到区块）→ 保存为备份配置 → 点击**备份**。
   备份会调用同一 Python 解释器运行 `backup_runner.py` 完成裁剪与打包。

**停止服务**：在服务窗口按 `Ctrl+C`，窗口会自动关闭；若启动失败，窗口会打印报错并**等待回车**，方便排查。

**命令行参数**（可选，加在 `python server.py` 后面；用 `.bat` 时可把它们追加到 `start_map.bat` 的调用里）：

| 参数 | 说明 |
| --- | --- |
| `--world <存档目录>` | 启动即加载该存档（路径会记到 `map_selector/world.json`） |
| `--port <端口>` | 指定起始端口，默认 `8787` |
| `--no-browser` | 启动后不自动打开浏览器 |
| `--verbose` | 打印详细日志 |

手动启动（等价于 `.bat` 做的事）：

```bash
cd map_selector
python server.py            # 可选：--world "路径" --port 8787 --no-browser --verbose
```

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

## 目录结构

```
.
├─ start_map.bat            # 网页选区工具的根目录入口（推荐双击）
├─ run_script.bat           # 命令行备份入口（python script.py）
├─ script.py                # 原始命令行备份调度
├─ backup_runner.py         # 实际执行裁剪/打包（网页工具的“备份”按钮也调用它）
├─ global_config.json       # 语言、config 读取路径等全局设置
├─ requirements.txt         # 依赖说明（本项目仅需 Python 标准库）
├─ configs/                 # 备份配置（内含模板与说明；个人配置默认不纳入版本控制）
└─ map_selector/            # 网页选区工具
   ├─ start_map.bat         # 本工具的启动入口
   ├─ server.py             # 本地 HTTP 服务 + 瓦片/活动/备份接口
   ├─ renderer.py           # MCA/NBT 解析与地图渲染
   └─ public/               # 前端（原生 JS，无构建步骤）
```

---

## 关于依赖 / `requirements.txt`

本项目的全部代码只使用 **Python 标准库**，没有任何第三方依赖，因此不需要执行
`pip install -r requirements.txt`。`requirements.txt` 现仅作为依赖说明保留。

---

## 许可与来源声明

- 本 fork 中对**新增/重写**的代码（主要是 `map_selector/` 网页工具与启动脚本）采用 **GNU AGPL-3.0**，见 [`LICENSE`](./LICENSE) 与 [`NOTICE`](./NOTICE)。采用 AGPL 的意图是：本作品保持自由，且不以闭源形式被商用；通过网络提供该服务时也须开放源码。
- **上游 [`Yinhe2332767/PartialBackuper`](https://github.com/Yinhe2332767/PartialBackuper) 目前没有许可证**（法律上默认“保留所有权利”）。因此：
  1. 若原作者提出要求，本仓库将下线（设为私有或删除）。
  2. 若上游日后为其代码补充许可证，本 fork 将针对继承而来的代码相应调整本仓库的许可条款。
- `script.py`、`backup_runner.py`、`global_config.json`、`requirements.txt`、`run_script.bat`、`configs/` 模板与说明、`README.txt` 等继承文件的著作权归原作者。

## 致谢

原作者 **Yinhe233**（原仓库说明：“作者：Yinhe233，主要代码由 AI 生成”）。
