# BDND - Baidu Netdisk Client

一个用于百度网盘API的Python客户端，支持通过pip安装并提供命令行工具。

[![GitHub](https://img.shields.io/github/stars/Rookie-Package/bdnd?style=social)](https://github.com/Rookie-Package/bdnd)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI](https://img.shields.io/pypi/v/bdnd)](https://pypi.org/project/bdnd/)

## 功能特性

- 📤 上传文件和目录到百度网盘
- 📥 从百度网盘下载文件和目录
- 📋 列出网盘文件
- 📊 获取用户信息和配额信息
- 🚀 支持断点续传
- 📈 显示上传/下载进度条
- 💻 交互式 Shell 支持（类似 Linux 命令）
- 📝 查看文件内容（cat, head, tail）
- 📊 CSV 文件查看和筛选（rcsv）
- 🔍 支持通配符匹配（*, ?）
- 📜 支持批量脚本执行

## 安装

### 方式一：使用 pip（推荐）

```bash
pip install bdnd
```

### 方式二：Windows 安装包

对于 Windows 用户，也可以下载预编译的安装包：

1. 从 [Releases](https://github.com/Rookie-Package/bdnd/releases) 下载 `bdnd-setup-x.x.x.exe`
2. 运行安装程序，按照提示完成安装
3. 安装完成后，可以在命令行中使用 `bdnd` 命令

**注意：** 如果使用安装包，无需安装 Python 环境。

**自行构建：** 如需自行构建 Windows 安装包，请参考 [BUILD_WINDOWS.md](BUILD_WINDOWS.md)

## 快速开始

### CLI 使用

安装后，你可以直接使用 `bdnd` 命令：

#### 基本文件操作

```bash
# 上传文件到网盘
bdnd /path/to/local/file /path/on/baidu/pan

# 下载文件
bdnd /path/on/baidu/pan /path/to/local/file

# 明确指定模式
bdnd --mode upload /local/dir /remote/dir/
bdnd --mode download /remote/dir/ /local/dir/

# 指定access token
bdnd --access-token YOUR_TOKEN /local/file /remote/file
```

#### 交互式 Shell

进入交互式 Shell，支持类似 Linux 的命令操作：

```bash
# 进入交互式 Shell
bdnd

# 设置默认工作路径
bdnd --set-home /apps/autodl

# 查看当前默认路径
bdnd --show-home
```

在交互式 Shell 中，你可以使用以下命令：

- `cd [path]` - 切换目录（支持 `cd ..`）
- `ls [path] [-s]` - 列出文件（`-s` 显示目录大小，支持通配符 `*`, `?`）
- `pwd` - 显示当前路径
- `du [path] [-s]` - 显示磁盘使用情况
- `mkdir <path>` - 创建目录
- `upload <local_path> [remote_path]` - 上传文件或目录
- `download <remote_path> [local_path]` - 下载文件或目录
- `mv <old_path> <new_name>` - 重命名文件或目录（支持通配符）
- `cat <path>` - 查看文件内容和信息
- `head [-n N] <path>` - 查看文件前 N 行（默认 10 行）
- `tail [-n N] <path>` - 查看文件后 N 行（默认 10 行）
- `rcsv [-n N] [-c] [-s col1,col2,...] <path>` - 查看 CSV 文件（类似 SQL SELECT）
- `whoami` - 显示用户和配额信息
- `clear` - 清屏
- `help [command]` - 显示帮助信息
- `exit` / `quit` - 退出 Shell

#### 批量脚本执行

支持执行 `.bdnd` 脚本文件：

```bash
# 执行批量脚本
bdnd script.bdnd
```

脚本示例（`script.bdnd`）：
```bash
cd /apps/autodl
ls
mkdir test
upload ./local_file.txt test/
```

### Python API 使用

```python
from bdnd import BaiduNetdiskClient

# 创建客户端
client = BaiduNetdiskClient(access_token="YOUR_ACCESS_TOKEN")

# 上传文件
client.upload_file_auto("local_file.txt", "/remote/path/file.txt")

# 上传目录
client.upload_directory("local_dir", "/remote/dir/", recursive=True)

# 下载文件
client.download_file_by_path("/remote/path/file.txt", "local_file.txt")

# 下载目录
client.download_directory("/remote/dir/", "local_dir", recursive=True)

# 列出文件（返回列表）
files = client.list_files(directory="/apps/autodl")
for file_info in files:
    print(f"{file_info.get('server_filename')}: {file_info.get('size')} bytes")

# 获取用户信息
user_info = client.get_user_info()

# 获取配额信息
quota = client.get_quota()
```

## 配置

### 环境变量

你可以通过环境变量设置 access token：

```bash
export baidu_netdisk_access_token="YOUR_ACCESS_TOKEN"
```

CLI会自动从环境变量读取。

### 默认工作路径

你可以设置默认的工作路径，这样在交互式 Shell 中会自动切换到该路径：

```bash
# 设置默认路径
bdnd --set-home /apps/autodl

# 查看当前默认路径
bdnd --show-home
```

设置后，每次进入交互式 Shell 都会自动切换到该路径。

## 获取 Access Token

你需要从百度开放平台获取 access token。可以使用以下方法构建授权URL：

```python
from bdnd import BaiduNetdiskClient

# 构建授权URL
auth_url = BaiduNetdiskClient.build_authorize_url(
    client_id="YOUR_CLIENT_ID",
    redirect_uri="oob"
)
print(auth_url)
```

访问该URL并授权后，可以从重定向URL中获取 access token。

## 依赖

- requests >= 2.25.0
- tqdm >= 4.60.0
- urllib3 >= 1.26.0
- env-key-manager >= 0.1.0
- tabulate >= 0.9.0

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

项目地址: [https://github.com/Rookie-Package/bdnd](https://github.com/Rookie-Package/bdnd)

## 更新日志

### 1.1.0
- 交互式 Shell 支持
- 支持常用 Linux 命令（cd, ls, pwd, mkdir, upload, download, mv, cat, head, tail, rcsv, whoami）
- 支持通配符匹配（*, ?）
- 支持批量脚本执行（.bdnd 文件）
- 支持设置默认工作路径
- CSV 文件查看和筛选功能
- 命令自动补全支持
- 新增 Windows 安装包支持（PyInstaller）
- 改进代理处理，自动禁用系统代理设置
- 更新依赖：移除 pandas 和 numpy，添加 tabulate

### 1.0.0
- 初始版本
- 支持文件上传/下载
- 支持目录上传/下载
- CLI工具支持


