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
    version="1.1.1",
    description="Baidu Netdisk Client - A Python client for Baidu Netdisk API with CLI support",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="Rookie",
    author_email="RookieEmail@163.com",
    url="https://github.com/Rookie-Package/bdnd",
    packages=find_packages(),
    include_package_data=True,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
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

