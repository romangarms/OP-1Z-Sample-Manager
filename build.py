#!/usr/bin/env python3
"""
Cross-platform build script for OP-Z Sample Manager.
Downloads platform-specific FFMPEG and builds the application.
"""

import os
import sys
import shutil
import subprocess
import urllib.request
import tarfile
import zipfile
import tempfile

# FFMPEG download URLs
FFMPEG_URLS = {
    "darwin": {
        # martin-riedl.de provides signed and notarized builds for macOS
        # URL pattern: /redirect/latest/macos/{arm64,amd64}/release/ffmpeg.zip
        "arm64": "https://ffmpeg.martin-riedl.de/redirect/latest/macos/arm64/release/ffmpeg.zip",
        "x86_64": "https://ffmpeg.martin-riedl.de/redirect/latest/macos/amd64/release/ffmpeg.zip",
    },
    "win32": {
        # gyan.dev essentials build for Windows
        "url": "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
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
    if sys.platform == "win32":
        return os.path.join(bin_dir, "ffmpeg.exe")
    else:  # this is either linux or macos or some strange os that I've never heard of. use the unix which path to try and find, else default to bin/ffmpeg
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg:
            return ffmpeg
        return os.path.join(bin_dir, "ffmpeg")

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

    # Get architecture-specific URL
    arch = get_macos_arch()
    url = FFMPEG_URLS["darwin"][arch]

    print(f"Detected macOS architecture: {arch}")

    # Download to temp file
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        if not download_file(url, tmp_path, f"FFMPEG for macOS ({arch})"):
            return False

        # Extract ffmpeg from the zip archive
        print("Extracting FFMPEG...")
        with zipfile.ZipFile(tmp_path, 'r') as zf:
            # The zip contains just the ffmpeg binary
            for name in zf.namelist():
                if name == "ffmpeg" or name.endswith("/ffmpeg"):
                    with zf.open(name) as src, open(ffmpeg_path, 'wb') as dst:
                        dst.write(src.read())
                    # Make executable
                    os.chmod(ffmpeg_path, 0o755)
                    print(f"FFMPEG installed to: {ffmpeg_path}")
                    return True

            # If no ffmpeg found, try extracting first file (might just be ffmpeg)
            names = zf.namelist()
            if len(names) == 1:
                with zf.open(names[0]) as src, open(ffmpeg_path, 'wb') as dst:
                    dst.write(src.read())
                os.chmod(ffmpeg_path, 0o755)
                print(f"FFMPEG installed to: {ffmpeg_path}")
                return True

        print("Error: ffmpeg not found in archive")
        return False
    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def download_ffmpeg_windows():
    """Download and extract FFMPEG for Windows."""
    bin_dir = get_bin_dir()
    os.makedirs(bin_dir, exist_ok=True)

    ffmpeg_path = get_ffmpeg_path()
    url = FFMPEG_URLS["win32"]["url"]

    # Download to temp file
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        if not download_file(url, tmp_path, "FFMPEG for Windows"):
            return False

        # Extract ffmpeg.exe from the archive
        print("Extracting FFMPEG...")
        with zipfile.ZipFile(tmp_path, 'r') as zf:
            # Find ffmpeg.exe in the archive
            for name in zf.namelist():
                if name.endswith("bin/ffmpeg.exe"):
                    # Extract to temp location then move
                    with tempfile.TemporaryDirectory() as extract_dir:
                        zf.extract(name, extract_dir)
                        extracted_path = os.path.join(extract_dir, name)
                        shutil.copy2(extracted_path, ffmpeg_path)
                    print(f"FFMPEG installed to: {ffmpeg_path}")
                    return True

        print("Error: ffmpeg.exe not found in archive")
        return False
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
    elif sys.platform == "linux":
        print("On Linux, FFMPEG should be installed via your package manager:")
        print("  Ubuntu/Debian: sudo apt install ffmpeg")
        print("  Fedora: sudo dnf install ffmpeg")
        print("  Arch: sudo pacman -S ffmpeg")
        print("You may also place the FFMPEG binary manually in the bin/ directory.")
        return False  # Continue build anyway
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
    spec_file = os.path.join(script_dir, "opz-sample-manager.spec")

    print("Running PyInstaller...")
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", spec_file],
        cwd=script_dir
    )

    return result.returncode == 0


def main():
    """Main build process."""
    print("=" * 60)
    print("OP-Z Sample Manager Build Script")
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
        print("App bundle: dist/OP-Z Sample Manager.app")
    elif sys.platform == "linux":
        print("Output folder: dist/opz-sample-manager/")
    else:
        print("Output: dist/OP-Z Sample Manager/")


if __name__ == "__main__":
    main()
