#!/usr/bin/env python3
"""
Cross-platform build script for OP-1Z Sample Manager.
Downloads platform-specific FFMPEG and builds the application.
"""

import os
import sys
import shutil
import subprocess
import urllib.request
import tempfile
import gzip

# FFMPEG download URLs
FFMPEG_URLS = {
    "darwin": {
        # eugeneware/ffmpeg-static publishes per-platform binaries on GitHub Releases
        "arm64": "https://github.com/eugeneware/ffmpeg-static/releases/latest/download/ffmpeg-darwin-arm64.gz",
        "x86_64": "https://github.com/eugeneware/ffmpeg-static/releases/latest/download/ffmpeg-darwin-x64.gz",
    },
    "win32": {
        "x64": "https://github.com/eugeneware/ffmpeg-static/releases/latest/download/ffmpeg-win32-x64.gz",
    }
}


def get_script_dir():
    """Get the directory containing this script."""
    return os.path.dirname(os.path.abspath(__file__))


def get_bin_dir():
    """Get the bin directory path."""
    return os.path.join(get_script_dir(), "bin")


def get_ffmpeg_path():
    """Get the expected FFMPEG binary path for the current platform."""
    bin_dir = get_bin_dir()
    if sys.platform == "darwin":
        return os.path.join(bin_dir, "ffmpeg")
    else:  # Windows
        return os.path.join(bin_dir, "ffmpeg.exe")


def download_file(url, dest_path, description="file"):
    """Download a file with progress indicator."""
    print(f"Downloading {description}...")
    print(f"  URL: {url}")

    def reporthook(block_num, block_size, total_size):
        if total_size > 0:
            downloaded = block_num * block_size
            percent = min(100, downloaded * 100 // total_size)
            print(f"\r  Progress: {percent}%", end="", flush=True)

    try:
        urllib.request.urlretrieve(url, dest_path, reporthook)
        print()  # New line after progress
        return True
    except Exception as e:
        print(f"\nError downloading: {e}")
        return False


def get_macos_arch():
    """Get the macOS architecture."""
    import platform
    machine = platform.machine()
    if machine == "arm64":
        return "arm64"
    else:
        return "x86_64"


def download_ffmpeg_macos():
    """Download and extract FFMPEG for macOS."""
    bin_dir = get_bin_dir()
    os.makedirs(bin_dir, exist_ok=True)

    ffmpeg_path = get_ffmpeg_path()

    arch = get_macos_arch()
    url = FFMPEG_URLS["darwin"][arch]

    print(f"Detected macOS architecture: {arch}")

    # Download to temp file
    with tempfile.NamedTemporaryFile(suffix=".gz", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        if not download_file(url, tmp_path, f"FFMPEG for macOS ({arch})"):
            return False

        # Extract ffmpeg from gzipped binary.
        print("Extracting FFMPEG...")
        with gzip.open(tmp_path, 'rb') as src, open(ffmpeg_path, 'wb') as dst:
            shutil.copyfileobj(src, dst)
        os.chmod(ffmpeg_path, 0o755)
        print(f"FFMPEG installed to: {ffmpeg_path}")
        return True
    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def download_ffmpeg_windows():
    """Download and extract FFMPEG for Windows."""
    bin_dir = get_bin_dir()
    os.makedirs(bin_dir, exist_ok=True)

    ffmpeg_path = get_ffmpeg_path()
    url = FFMPEG_URLS["win32"]["x64"]
    # Download to temp file
    with tempfile.NamedTemporaryFile(suffix=".gz", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        if not download_file(url, tmp_path, "FFMPEG for Windows"):
            return False

        # Extract ffmpeg.exe from gzipped binary.
        print("Extracting FFMPEG...")
        with gzip.open(tmp_path, 'rb') as src, open(ffmpeg_path, 'wb') as dst:
            shutil.copyfileobj(src, dst)
        print(f"FFMPEG installed to: {ffmpeg_path}")
        return True
    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def ensure_ffmpeg():
    """Ensure FFMPEG is available, downloading if necessary."""
    ffmpeg_path = get_ffmpeg_path()

    if os.path.exists(ffmpeg_path):
        print(f"FFMPEG already exists: {ffmpeg_path}")
        return True

    print("FFMPEG not found, downloading...")

    if sys.platform == "darwin":
        return download_ffmpeg_macos()
    elif sys.platform == "win32":
        return download_ffmpeg_windows()
    else:
        print(f"Unsupported platform: {sys.platform}")
        print("Please manually place the FFMPEG binary in the bin/ directory.")
        return False


def clean_build():
    """Clean previous build and dist directories."""
    script_dir = get_script_dir()

    for dirname in ["build", "dist"]:
        path = os.path.join(script_dir, dirname)
        if os.path.exists(path):
            print(f"Removing {dirname}/...")
            shutil.rmtree(path)


def run_pyinstaller():
    """Run PyInstaller with the spec file."""
    script_dir = get_script_dir()
    spec_file = os.path.join(script_dir, "op-1z-sample-manager.spec")

    print("Running PyInstaller...")
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", spec_file],
        cwd=script_dir
    )

    return result.returncode == 0


def main():
    """Main build process."""
    print("=" * 60)
    print("OP-1Z Sample Manager Build Script")
    print("=" * 60)
    print()

    # Step 1: Ensure FFMPEG is available
    print("Step 1: Checking FFMPEG...")
    if not ensure_ffmpeg():
        print("\nBuild failed: Could not obtain FFMPEG")
        print("You can manually download FFMPEG and place it in the bin/ directory.")
        sys.exit(1)
    print()

    # Step 2: Clean previous builds
    print("Step 2: Cleaning previous builds...")
    clean_build()
    print()

    # Step 3: Run PyInstaller
    print("Step 3: Building application...")
    if not run_pyinstaller():
        print("\nBuild failed: PyInstaller error")
        sys.exit(1)

    print()
    print("=" * 60)
    print("Build complete!")
    print("=" * 60)

    if sys.platform == "darwin":
        print("App bundle: dist/OP-1Z Sample Manager.app")
    else:
        print("Output: dist/OP-1Z Sample Manager/")


if __name__ == "__main__":
    main()
