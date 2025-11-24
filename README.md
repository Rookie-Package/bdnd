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

## 安装

```bash
pip install bdnd
```

## 快速开始

### CLI 使用

安装后，你可以直接使用 `bdnd` 命令：

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

# 列出文件
files = client.list_files(directory="/apps/autodl")

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

- requests
- tqdm
- pandas
- urllib3
- env-key-manager

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

项目地址: [https://github.com/Rookie-Package/bdnd](https://github.com/Rookie-Package/bdnd)

## 更新日志

### 1.0.0
- 初始版本
- 支持文件上传/下载
- 支持目录上传/下载
- CLI工具支持

