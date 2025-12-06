"""
Script to publish bdnd to PyPI
This script automates the publishing process
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def check_dependencies():
    """Check if required build tools are installed"""
    required_packages = ['build', 'twine']
    missing = []
    
    # Check build module
    try:
        import build
    except ImportError:
        missing.append('build')
    
    # Check twine module
    try:
        import twine
    except ImportError:
        missing.append('twine')
    
    if missing:
        print(f"Missing required packages: {', '.join(missing)}")
        print("Installing missing packages...")
        
        # Disable proxy for pip install
        env = os.environ.copy()
        env.pop('HTTP_PROXY', None)
        env.pop('HTTPS_PROXY', None)
        env.pop('http_proxy', None)
        env.pop('https_proxy', None)
        
        try:
            subprocess.check_call(
                [sys.executable, '-m', 'pip', 'install'] + missing,
                env=env
            )
            print("Dependencies installed successfully!")
        except subprocess.CalledProcessError as e:
            print(f"Error installing dependencies: {e}")
            return False
    return True

def clean_build_dirs():
    """Clean previous build directories"""
    dirs_to_clean = ['build', 'dist', '*.egg-info']
    for pattern in dirs_to_clean:
        if '*' in pattern:
            # Use glob for patterns
            for path in Path('.').glob(pattern):
                if path.is_dir():
                    print(f"Cleaning {path}...")
                    shutil.rmtree(path)
                else:
                    print(f"Removing {path}...")
                    path.unlink()
        else:
            if os.path.exists(pattern):
                print(f"Cleaning {pattern}...")
                shutil.rmtree(pattern)

def build_package():
    """Build the package"""
    print("Building package...")
    
    # Disable proxy
    env = os.environ.copy()
    env.pop('HTTP_PROXY', None)
    env.pop('HTTPS_PROXY', None)
    env.pop('http_proxy', None)
    env.pop('https_proxy', None)
    
    try:
        subprocess.check_call(
            [sys.executable, '-m', 'build'],
            env=env
        )
        print("Package built successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error building package: {e}")
        return False

def check_package():
    """Check the built package"""
    print("Checking package...")
    
    dist_files = list(Path('dist').glob('*'))
    if not dist_files:
        print("Error: No package files found in dist/")
        return False
    
    # Disable proxy
    env = os.environ.copy()
    env.pop('HTTP_PROXY', None)
    env.pop('HTTPS_PROXY', None)
    env.pop('http_proxy', None)
    env.pop('https_proxy', None)
    
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'twine', 'check'] + [str(f) for f in dist_files],
            env=env,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("Package check passed!")
            return True
        else:
            print("Package check warnings/errors:")
            print(result.stdout)
            print(result.stderr)
            # Check if it's just a warning about license-file
            if 'license-file' in result.stderr.lower() or 'license-file' in result.stdout.lower():
                print("\nWarning: License file field issue detected.")
                print("This is often a false positive. The package should still work.")
                print("Do you want to continue anyway? (y/n): ", end='')
                choice = input().strip().lower()
                if choice in ['y', 'yes']:
                    return True
            return False
    except subprocess.CalledProcessError as e:
        print(f"Error checking package: {e}")
        return False

def upload_to_testpypi():
    """Upload to TestPyPI"""
    print("Uploading to TestPyPI...")
    
    dist_files = list(Path('dist').glob('*'))
    if not dist_files:
        print("Error: No package files found in dist/")
        return False
    
    # Disable proxy
    env = os.environ.copy()
    env.pop('HTTP_PROXY', None)
    env.pop('HTTPS_PROXY', None)
    env.pop('http_proxy', None)
    env.pop('https_proxy', None)
    
    try:
        subprocess.check_call(
            [sys.executable, '-m', 'twine', 'upload', '--repository', 'testpypi'] + [str(f) for f in dist_files],
            env=env
        )
        print("Uploaded to TestPyPI successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error uploading to TestPyPI: {e}")
        return False

def upload_to_pypi():
    """Upload to PyPI"""
    print("Uploading to PyPI...")
    
    dist_files = list(Path('dist').glob('*'))
    if not dist_files:
        print("Error: No package files found in dist/")
        return False
    
    # Disable proxy
    env = os.environ.copy()
    env.pop('HTTP_PROXY', None)
    env.pop('HTTPS_PROXY', None)
    env.pop('http_proxy', None)
    env.pop('https_proxy', None)
    
    try:
        subprocess.check_call(
            [sys.executable, '-m', 'twine', 'upload'] + [str(f) for f in dist_files],
            env=env
        )
        print("Uploaded to PyPI successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error uploading to PyPI: {e}")
        return False

def main():
    """Main publishing process"""
    print("=" * 60)
    print("BDND PyPI Publishing Script")
    print("=" * 60)
    print()
    
    # Check if we're in the right directory
    if not os.path.exists('setup.py') or not os.path.exists('pyproject.toml'):
        print("Error: Must run from project root directory")
        return 1
    
    # Check dependencies
    print("Step 1: Checking dependencies...")
    if not check_dependencies():
        return 1
    print()
    
    # Clean previous builds
    print("Step 2: Cleaning previous builds...")
    clean_build_dirs()
    print()
    
    # Build package
    print("Step 3: Building package...")
    if not build_package():
        return 1
    print()
    
    # Check package
    print("Step 4: Checking package...")
    if not check_package():
        return 1
    print()
    
    # Ask for confirmation
    print("=" * 60)
    print("Package is ready for upload!")
    print("=" * 60)
    print()
    print("Options:")
    print("  1. Upload to TestPyPI (recommended for testing)")
    print("  2. Upload to PyPI (production)")
    print("  3. Exit without uploading")
    print()
    
    choice = input("Enter your choice (1/2/3): ").strip()
    
    if choice == '1':
        if upload_to_testpypi():
            print()
            print("=" * 60)
            print("Successfully uploaded to TestPyPI!")
            print("=" * 60)
            print()
            print("You can test the installation with:")
            print("  pip install --index-url https://test.pypi.org/simple/ bdnd")
            return 0
        else:
            return 1
    elif choice == '2':
        confirm = input("Are you sure you want to upload to PyPI? (yes/no): ").strip().lower()
        if confirm in ['yes', 'y']:
            if upload_to_pypi():
                print()
                print("=" * 60)
                print("Successfully uploaded to PyPI!")
                print("=" * 60)
                print()
                print("Package is now available at:")
                print("  https://pypi.org/project/bdnd/")
                return 0
            else:
                return 1
        else:
            print("Upload cancelled.")
            return 0
    else:
        print("Exiting without uploading.")
        return 0

if __name__ == '__main__':
    sys.exit(main())

