"""
Build Windows installer for bdnd
This script helps build Windows executable and installer
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# Disable proxy for all requests in this script
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)

def check_dependencies():
    """Check if required build tools are installed"""
    required = ['PyInstaller']
    missing = []
    
    for package in required:
        try:
            if package == 'PyInstaller':
                # Check PyInstaller specifically
                import PyInstaller
            else:
                __import__(package)
        except ImportError:
            missing.append('pyinstaller' if package == 'PyInstaller' else package)
    
    if missing:
        print(f"Missing required packages: {', '.join(missing)}")
        print("Installing missing packages...")
        
        # Disable proxy for pip install
        env = os.environ.copy()
        env.pop('HTTP_PROXY', None)
        env.pop('HTTPS_PROXY', None)
        env.pop('http_proxy', None)
        env.pop('https_proxy', None)
        
        # Try to install with proxy disabled
        try:
            subprocess.check_call(
                [sys.executable, '-m', 'pip', 'install', '--no-proxy', '*'] + missing,
                env=env
            )
            print("Dependencies installed successfully!")
        except subprocess.CalledProcessError:
            # If that fails, try without --no-proxy flag
            try:
                subprocess.check_call(
                    [sys.executable, '-m', 'pip', 'install'] + missing,
                    env=env
                )
                print("Dependencies installed successfully!")
            except subprocess.CalledProcessError as e:
                print(f"\nError: Failed to install dependencies: {e}")
                print("\nPlease try installing manually:")
                print(f"  pip install {' '.join(missing)}")
                print("\nOr disable proxy settings:")
                print("  pip install --no-proxy '*' " + ' '.join(missing))
                print("\nOr set environment variables:")
                print("  set HTTP_PROXY=")
                print("  set HTTPS_PROXY=")
                print("  pip install " + ' '.join(missing))
                return False
    return True

def clean_build_dirs():
    """Clean previous build directories"""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"Cleaning {dir_name}...")
            shutil.rmtree(dir_name)
    
    # Clean .spec file artifacts
    for spec_file in Path('.').glob('*.spec'):
        if spec_file.name != 'bdnd.spec':
            spec_file.unlink()

def build_executable():
    """Build Windows executable using PyInstaller"""
    print("Building Windows executable...")
    
    # Check if spec file exists
    if not os.path.exists('bdnd.spec'):
        print("Error: bdnd.spec file not found!")
        return False
    
    # Build using PyInstaller
    cmd = [sys.executable, '-m', 'PyInstaller', 'bdnd.spec', '--clean', '--noconfirm']
    
    try:
        subprocess.check_call(cmd)
        print("Executable built successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error building executable: {e}")
        return False

def create_installer_script():
    """Create a simple installer batch script"""
    installer_content = """@echo off
echo ========================================
echo BDND Windows Installer
echo ========================================
echo.

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo This installer requires administrator privileges.
    echo Please run as administrator.
    pause
    exit /b 1
)

echo Installing BDND...
echo.

REM Create installation directory
set INSTALL_DIR=%ProgramFiles%\\BDND
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

REM Copy files
echo Copying files...
xcopy /E /I /Y "dist\\bdnd.exe" "%INSTALL_DIR%\\"

REM Add to PATH
echo Adding to PATH...
setx PATH "%PATH%;%INSTALL_DIR%" /M

echo.
echo ========================================
echo Installation completed!
echo ========================================
echo.
echo BDND has been installed to: %INSTALL_DIR%
echo You can now use 'bdnd' command from anywhere.
echo.
pause
"""
    
    with open('install.bat', 'w', encoding='utf-8') as f:
        f.write(installer_content)
    
    print("Installer script created: install.bat")

def main():
    """Main build process"""
    print("=" * 50)
    print("BDND Windows Build Script")
    print("=" * 50)
    print()
    
    # Check dependencies
    print("Step 1: Checking dependencies...")
    if not check_dependencies():
        print("Build aborted due to dependency installation failure.")
        return 1
    print()
    
    # Clean previous builds
    print("Step 2: Cleaning previous builds...")
    clean_build_dirs()
    print()
    
    # Build executable
    print("Step 3: Building executable...")
    if not build_executable():
        print("Build failed!")
        return 1
    print()
    
    # Create installer script
    print("Step 4: Creating installer script...")
    create_installer_script()
    print()
    
    print("=" * 50)
    print("Build completed successfully!")
    print("=" * 50)
    print()
    print("Output files:")
    print("  - dist/bdnd.exe: Standalone executable")
    print("  - install.bat: Simple installer script")
    print()
    print("To create a proper installer, consider using:")
    print("  - Inno Setup (https://jrsoftware.org/isinfo.php)")
    print("  - NSIS (https://nsis.sourceforge.io/)")
    print("  - WiX Toolset (https://wixtoolset.org/)")
    print()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

