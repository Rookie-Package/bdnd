"""Setup script for bdnd package"""

from setuptools import setup, find_packages
import os

# Read README file
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), "README.md")
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

setup(
    name="bdnd",
    version="1.0.0",
    description="Baidu Netdisk Client - A Python client for Baidu Netdisk API with CLI support",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="Rookie",
    author_email="RookieEmail@163.com",
    url="https://github.com/Rookie-Package/bdnd",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.7",
    install_requires=[
        "requests>=2.25.0",
        "tqdm>=4.60.0",
        "urllib3>=1.26.0",
        "env-key-manager>=0.1.0",
        "tabulate>=0.9.0",
    ],
    entry_points={
        "console_scripts": [
            "bdnd=bdnd.cli:main",
        ],
    },
    keywords="baidu netdisk api client cli upload download",
    project_urls={
        "Bug Reports": "https://github.com/Rookie-Package/bdnd/issues",
        "Source": "https://github.com/Rookie-Package/bdnd",
        "Documentation": "https://github.com/Rookie-Package/bdnd#readme",
    },
)

