# 发布指南

本指南说明如何将 `bdnd` 包发布到 PyPI。

## 准备工作

1. **注册 PyPI 账户**
   - 访问 https://pypi.org/account/register/ 注册账户
   - 验证邮箱并设置账户

2. **创建 API Token (推荐)**
   - 登录 PyPI 后，访问 https://pypi.org/manage/account/token/
   - 创建新的 API Token，选择 "Entire account" 范围
   - 复制生成的 token (格式: `pypi-...`)

3. **配置 .pypirc**
   ```bash
   cp .pypirc.example .pypirc
   ```
   编辑 `.pypirc` 文件，填入你的 API Token

## 构建和发布

### 1. 更新版本号

在以下文件中更新版本号：
- `bdnd/__init__.py` 中的 `__version__`
- `setup.py` 中的 `version`

### 2. 清理旧的构建文件

```bash
# Windows
rmdir /s /q build dist *.egg-info

# Linux/Mac
rm -rf build dist *.egg-info
```

### 3. 构建分发包

```bash
pip install --upgrade build twine
python -m build
```

这会生成 `dist/` 目录，包含 `.whl` 和 `.tar.gz` 文件。

### 4. 检查构建的包

```bash
twine check dist/*
```

### 5. 测试发布到 TestPyPI (可选但推荐)

```bash
twine upload --repository testpypi dist/*
```

然后在测试环境中安装：
```bash
pip install --index-url https://test.pypi.org/simple/ bdnd
```

### 6. 发布到 PyPI

```bash
twine upload dist/*
```

或者如果配置了 `.pypirc`：
```bash
twine upload dist/*
```

### 7. 验证发布

```bash
pip install bdnd
bdnd --help
```

## 更新现有包

如果需要更新已发布的包：

1. 更新版本号
2. 按照上述步骤重新构建和发布

## 注意事项

- 版本号必须递增，不能重复使用
- 确保 `README.md` 格式正确
- 确保所有依赖都在 `setup.py` 的 `install_requires` 中列出
- 建议先发布到 TestPyPI 进行测试

## 常见问题

### 错误: "File already exists"
这意味着该版本已经发布过，需要更新版本号。

### 错误: 认证失败
检查 `.pypirc` 文件中的 token 是否正确，或者使用环境变量：
```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-your-token-here
```

