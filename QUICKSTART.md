# 快速入门指南

## 安装

```bash
pip install bdnd
```

## 基本使用

### 命令行使用

安装后，你可以直接使用 `bdnd` 命令（无需 `python` 前缀）：

```bash
# 设置环境变量（可选，也可以在命令行中指定）
export baidu_netdisk_access_token="YOUR_ACCESS_TOKEN"

# 上传文件
bdnd /path/to/local/file.txt /remote/path/file.txt

# 下载文件
bdnd /remote/path/file.txt /path/to/local/file.txt

# 上传目录
bdnd /local/directory /remote/directory/

# 下载目录
bdnd /remote/directory/ /local/directory

# 明确指定模式
bdnd --mode upload /local/file.txt /remote/file.txt
bdnd --mode download /remote/file.txt /local/file.txt

# 使用命令行参数指定token
bdnd --access-token YOUR_TOKEN /local/file.txt /remote/file.txt
```

### Python API 使用

```python
from bdnd import BaiduNetdiskClient

# 方式1: 使用环境变量
import os
os.environ['baidu_netdisk_access_token'] = 'YOUR_ACCESS_TOKEN'
client = BaiduNetdiskClient()

# 方式2: 直接传入token
client = BaiduNetdiskClient(access_token="YOUR_ACCESS_TOKEN")

# 或者后续设置
client = BaiduNetdiskClient()
client.set_access_token("YOUR_ACCESS_TOKEN")

# 上传单个文件
client.upload_file_auto(
    file_path="local_file.txt",
    save_path="/remote/path/file.txt",
    show_progress=True
)

# 上传整个目录
count = client.upload_directory(
    local_dir="./local_directory",
    remote_dir="/remote/directory/",
    recursive=True
)
print(f"成功上传 {count} 个文件")

# 下载单个文件
client.download_file_by_path(
    file_path="/remote/path/file.txt",
    save_path="local_file.txt"
)

# 下载整个目录
count = client.download_directory(
    directory_path="/remote/directory/",
    save_dir="./local_directory",
    recursive=True
)
print(f"成功下载 {count} 个文件")

# 列出文件
files_df = client.list_files(
    directory="/apps/autodl",
    limit=100
)
print(files_df)

# 递归列出所有文件
all_files = client.list_all_files_recursive(path="/apps/autodl")
for file_info in all_files:
    print(f"{file_info['path']}: {file_info['size']} bytes")

# 获取用户信息
user_info = client.get_user_info()
print(f"用户名: {user_info.get('uname')}")

# 获取配额信息
quota = client.get_quota()
print(f"总空间: {quota.get('total')} bytes")
print(f"已用空间: {quota.get('used')} bytes")
```

## 获取 Access Token

1. 访问 [百度开放平台](https://open.baidu.com/)
2. 创建应用并获取 `client_id`
3. 使用以下代码生成授权URL：

```python
from bdnd import BaiduNetdiskClient

auth_url = BaiduNetdiskClient.build_authorize_url(
    client_id="YOUR_CLIENT_ID",
    redirect_uri="oob"
)
print(f"访问以下URL进行授权:\n{auth_url}")
```

4. 在浏览器中访问URL并授权
5. 从重定向URL中提取 `access_token`

## 常见使用场景

### 场景1: 定期备份目录

```python
from bdnd import BaiduNetdiskClient
import os

client = BaiduNetdiskClient(access_token=os.environ['baidu_netdisk_access_token'])

# 备份本地目录到网盘
client.upload_directory(
    local_dir="/path/to/backup",
    remote_dir="/backups/daily/",
    recursive=True
)
```

### 场景2: 批量下载文件

```python
from bdnd import BaiduNetdiskClient

client = BaiduNetdiskClient(access_token="YOUR_TOKEN")

# 列出所有文件
files = client.list_all_files_recursive(path="/apps/autodl")

# 筛选特定类型的文件
image_files = [f for f in files if f.get('category') == 1 and not f.get('isdir')]

# 下载每个文件
for file_info in image_files:
    save_path = f"./downloads/{file_info['server_filename']}"
    client.download_file_by_fsid(
        fsid=file_info['fs_id'],
        save_path=save_path
    )
```

### 场景3: 检查文件是否存在

```python
from bdnd import BaiduNetdiskClient

client = BaiduNetdiskClient(access_token="YOUR_TOKEN")

fsid = client.get_fsid_by_path("/remote/path/file.txt")
if fsid:
    print("文件存在")
    file_info = client.get_file_info([fsid])
    print(f"文件大小: {file_info[0].get('size')} bytes")
else:
    print("文件不存在")
```

## 注意事项

1. **Access Token 有效期**: Access token 可能有有效期限制，过期后需要重新获取
2. **文件路径**: 远程路径必须以 `/` 开头
3. **目录路径**: 目录路径建议以 `/` 结尾
4. **大文件上传**: 大文件会自动分块上传，支持断点续传
5. **进度显示**: 默认会显示上传/下载进度，可以通过 `show_progress=False` 禁用

## 故障排除

### 错误: "Access token not set"
- 确保设置了环境变量 `baidu_netdisk_access_token` 或通过参数传入

### 错误: "File not found"
- 检查本地文件路径是否正确
- 确保有读取权限

### 错误: SSL 错误
- 代码已自动处理 SSL 错误，如果仍有问题，检查网络连接

