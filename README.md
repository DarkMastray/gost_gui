这是一个为 [gost](https://github.com/ginuerzh/gost) 设计的简单 Python 图形界面封装工具。它可以帮助你摆脱命令行，通过直观的界面管理本地端口转发和 Socks5 代理。

## ✨ 功能特性

- **图形化配置**：支持本地端口、远程 IP/端口、Socks5 代理等参数的快速输入。
- **配置持久化**：输入内容自动保存，下次启动无需重复填写。
- **历史记录**：所有输入项均带下拉历史框，支持快速切换常用配置。
- **实时日志**：内置黑色极客风格控制台，实时抓取并滚动显示 `gost.exe` 的运行输出。
- **静默运行**：自动隐藏 `gost.exe` 的 CMD 黑框，保持桌面整洁。
- **安全清理**：关闭 GUI 窗口时会自动同步结束后台的 `gost` 进程，防止资源占用。

## 🚀 快速开始

### 1. 准备环境
- 确保已安装 Python 3.x。
- 下载 [gost 核心程序](https://github.com/go-gost/gost/releases/) (例如 `gost_3.2.6_windows_386.zip`)。

### 2. 运行脚本
直接运行主程序：
```bash
python gost_gui.py
```

### 3. 参数说明
- **Gost.exe 路径**：选择你下载的 `gost.exe` 文件位置。
- **本地端口**：你希望在本地监听的端口（例如 `33890`）。
- **远程 IP/端口**：目标服务器的地址和端口。
- **Socks5 代理**：用于中转的代理服务器地址和端口。

## 🛠️ 构建可执行文件 (.exe)

如果你想将其打包成独立的 EXE 文件，可以使用仓库中内置的 GitHub Actions，或者在本地执行：

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "GostGUI" gost_gui.py
```
打包完成后，可在 `dist` 目录下找到 `GostGUI.exe`。

## 📂 项目结构
- `gost_gui.py`: 主程序代码。
- `gost_history.json`: 自动生成的配置文件（存储历史输入）。
- `.github/workflows/build.yml`: GitHub 自动构建脚本。

## ⚖️ 免责声明
本工具仅为 `gost` 的 UI 封装，不提供任何代理服务。请在遵守当地法律法规的前提下使用。
