# ULI 平台 — 通用乐高接口（Universal LEGO Interface）

[English](README.md) | **中文文档**

> 把软件想象成乐高：一个个小应用，通过统一的“接口卡扣”拼在一起。
> 一次构建，处处复用。

ULI 是一个**本地优先**的平台，运行在你自己的电脑上。它可以：

- 同时运行多个互相独立的应用；
- 让它们通过安全、带校验的“接口”互相通信；
- 把一个现成的网站直接搬进来托管，**不改它一行代码**；
- 在画布上拖拽应用、连线，然后点 **Execute（执行）**。

不需要云服务、不需要注册账号、没有月费。所有东西都只在你电脑的
`127.0.0.1` 上运行。

---

## 😀 完全没用过命令行？从这里开始

你只需要复制粘贴几条命令，按顺序照做即可。

### 第 1 步 — 安装两个免费软件

| 软件 | 用途 | 下载地址 | 检查是否装好 |
|---|---|---|---|
| **Python 3.11 或更高** | 运行平台后端 | <https://www.python.org/downloads/> | `python --version` |
| **Node.js 18 或更高** | 构建用户界面 | <https://nodejs.org/> | `node --version` |

> ⚠️ **Windows 用户注意：** 安装 Python 的第一个界面里，**一定要勾选
> “Add python.exe to PATH”**，再点 Install。忘了勾选的话，安装脚本会提示
> 找不到 Python。

### 第 2 步 — 获取项目

**方式 A — 直接下载压缩包（最简单）：**

1. 在 GitHub 页面点绿色的 **`Code`** 按钮；
2. 点 **Download ZIP**，解压到一个简单的路径，例如
   `C:\uli-platform`。

**方式 B — 用 Git 克隆（已装 Git 的话）：**

```bash
git clone https://github.com/Zhuan-05/uli-platform.git
```

### 第 3 步 — 在项目文件夹里打开终端

- **Windows：** 用文件资源管理器打开 `uli-platform` 文件夹，点一下顶部的地址
  栏，输入 `cmd` 回车。会弹出一个黑色窗口，而且已经“在这个文件夹里”了。
- **macOS：** 右键文件夹 → **服务** → **新建位于文件夹位置的终端窗口**。
- **Linux：** 打开终端，用 `cd` 进入该文件夹。

### 第 4 步 — 安装（一条命令）

**Windows：**

```bat
scripts\setup.bat
```

**macOS / Linux：**

```bash
chmod +x scripts/*.sh
scripts/setup.sh
```

它会创建一个独立的 Python 环境、下载依赖、构建网页。第一次运行需要几分钟。
看到 **Setup complete** 就说明成功了。

### 第 5 步 — 启动

**Windows：**

```bat
scripts\run.bat
```

**macOS / Linux：**

```bash
scripts/run.sh
```

**这个窗口不要关** —— 它本身就是平台。你会看到：

```
Starting ULI Core on http://127.0.0.1:8787
UI:  http://127.0.0.1:8787/ui/
```

### 第 6 步 — 打开界面

在浏览器里访问：

## 👉 http://127.0.0.1:8787/ui/

---

## 🧭 前 5 分钟上手（带练）

1. **左侧菜单 → Applications（应用）。** 你会看到三块“乐高积木”：
   - *Inventory App*（库存应用）和 *Order App*（订单应用）——两个独立应用；
   - *Acme Catalogue* —— 一个**原样搬进来**的现成网站。
2. 先点 **Inventory App** 的 **Start**，再点 **Order App** 的 **Start**。
   状态徽章变绿 → `running`。
3. **左侧菜单 → Visual Builder（可视化搭建）。**
4. 点 **Load example flow（加载示例流程）**。出现三个方块，用箭头连在一起。
   中间的方块是 `order.create`。
5. 点 **Execute（执行）**。
   右侧 Result 面板会显示一个订单。注意里面的库存数字来自
   **Inventory App** —— 两个应用已经通过 ULI 互相通信了。🎉
6. **左侧菜单 → Themes（主题）**，在深色玻璃质感和浅色之间切换。
7. **左侧菜单 → Activity（活动日志）**，查看应用产生的事件。

### 每个菜单的作用

| 菜单 | 用途 |
|---|---|
| **Applications 应用** | 安装 / 启动 / 停止 / 删除应用 |
| **Capabilities 能力** | 查看每个应用“能做什么”（它的“接口插头”） |
| **Visual Builder 可视化搭建** | 把方块拖到画布、连线、运行流程 |
| **Blueprints 蓝图** | 保存的流程，可随时重新打开或再执行 |
| **Themes 主题** | 换外观，后端逻辑完全不受影响 |
| **Activity 活动日志** | 记录发生过的所有事情 |

---

## 🧩 两个“惊艳”功能，动手试试

### A. 把一个现成网站搬进来

**Applications → Import a prebuilt static website**，填上你电脑里某个包含
`index.html` 的**文件夹路径**，起个名字，点 **Import folder**，再点 **Open**。
网站的原始文件会被**原封不动**复制过来 —— ULI 不会改写你的代码。

### B. 把两个应用连起来

在 **Visual Builder** 里，点左侧列表里的能力 `inventory.check`，把它拖到画布
上；然后从一个方块右边的圆点拖到另一个方块左边的圆点。如果两个“插头”不匹配，
ULI **会拒绝连线并告诉你原因** —— 这是特性，不是 bug。

---

## ⏹ 停止、重启、重置

| 我想…… | 这样做 |
|---|---|
| 停止平台 | 关闭终端窗口，或在窗口里按 `Ctrl + C` |
| 再次启动 | 运行 `scripts\run.bat`（Windows）/ `scripts/run.sh`（macOS/Linux） |
| 换一个端口 | Windows：先 `set ULI_CORE_PORT=9000`，再运行 `scripts\run.bat` |
| 彻底重置 | 删除 `data` 文件夹，然后重新启动 |

`data/` 里存放注册表、你的蓝图、事件日志，以及导入的网站。

---

## 🆘 新手常见问题

| 现象 | 解决办法 |
|---|---|
| 提示“找不到 `python`” | 重装 Python，务必勾选 **Add python.exe to PATH** |
| 提示“找不到 `node`” | 重装 Node.js，然后重新打开终端 |
| 运行时说 `.venv` 不存在 | 先运行 `scripts\setup.bat` |
| 打开 `/` 只有纯文本，没有界面 | 界面还没构建：再运行一次 `scripts\setup.bat` |
| 网页打不开 | 确认 `run` 窗口还开着；确认端口是 8787 |
| 端口被占用 | 换一个端口，例如设置 `ULI_CORE_PORT=9000` |
| 导入的网站图片/CSS 出错 | 该网站用了根绝对路径，见 `docs/LEGACY_WEBSITE_IMPORT.md` |
| 崩溃了怎么办 | 去 `data/logs/` 看日志，每个应用都有自己的日志文件 |

更多请看：[`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md)

---

## 👩‍💻 给开发者

- **自动化测试：** `.venv/bin/python -m pytest tests -v`（共 35 个，全部通过）——
  见 [`docs/TEST_REPORT.md`](docs/TEST_REPORT.md)。
- **在线 API 文档：** <http://127.0.0.1:8787/docs>
- **架构说明：** [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- **接口规范：** [`docs/ULI_INTERFACE_SPEC.md`](docs/ULI_INTERFACE_SPEC.md)
- **开发原生应用：** [`docs/NATIVE_SDK_GUIDE.md`](docs/NATIVE_SDK_GUIDE.md)
- **打包与版本管理：** [`docs/MODULE_DEVELOPER_GUIDE.md`](docs/MODULE_DEVELOPER_GUIDE.md)
- **导入旧网站：** [`docs/LEGACY_WEBSITE_IMPORT.md`](docs/LEGACY_WEBSITE_IMPORT.md)
- **Windows 安装细节：** [`docs/WINDOWS_SETUP.md`](docs/WINDOWS_SETUP.md)
- **已知限制（建议先读）：** [`docs/KNOWN_LIMITATIONS.md`](docs/KNOWN_LIMITATIONS.md)
- **未来路线图：** [`docs/ROADMAP.md`](docs/ROADMAP.md)

项目目录结构：

```
core/                内核（注册表、API、校验）
uli_sdk/             开发新（原生）应用用的 SDK
runtime_adapters/    应用的托管方式（静态网站、本地进程、外部 URL…）
module_manager/      生命周期管理 + 应用之间的安全“代理”
compatibility/       清单规则与版本校验
event_bus/           带版本的事件系统
blueprints/          流程：结构定义、存储、执行
frontend/            网页界面（构建产物在 frontend/dist）
theme_design/        主题
applications/        示例应用（订单、库存）
examples/            一个可直接导入的现成网站
tests/               自动化测试
docs/                全部详细文档
scripts/             安装 / 启动 / 构建脚本
```

## 许可证

MIT 许可证 —— 见 [`LICENSE`](LICENSE)。

版权所有 (c) 2026 Zhuan-05。

你可以自由地使用、修改、分发本软件（包括商业用途），只需保留版权声明和许可声明。
本项目所有依赖均为宽松许可证（MIT / BSD / Apache-2.0）。
