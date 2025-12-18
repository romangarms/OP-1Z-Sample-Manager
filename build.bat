@echo off
REM Build script for OP-Z Sample Manager (Windows)

echo Building OP-Z Sample Manager...

REM Clean previous builds
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM Run PyInstaller
pyinstaller opz-sample-manager.spec

echo.
echo Build complete!
echo Output: dist\OP-Z Sample Manager\
