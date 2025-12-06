"""
Entry point for PyInstaller - redirects to bdnd.cli.main
This file is used when building with PyInstaller to avoid relative import issues.
"""

from bdnd.cli import main

if __name__ == '__main__':
    main()

