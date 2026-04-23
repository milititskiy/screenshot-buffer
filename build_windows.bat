@echo off
setlocal EnableDelayedExpansion

echo ============================================================
echo  Screenshot Buffer — Windows Build Script
echo ============================================================

:: ── 1. Install runtime dependencies ─────────────────────────────────
echo.
echo [1/4] Installing runtime dependencies...
pip install -r requirements.txt
if ERRORLEVEL 1 (
    echo ERROR: pip install failed.
    pause & exit /b 1
)

:: ── 2. Install PyInstaller ───────────────────────────────────────────
echo.
echo [2/4] Installing PyInstaller...
pip install pyinstaller>=6.0
if ERRORLEVEL 1 (
    echo ERROR: PyInstaller installation failed.
    pause & exit /b 1
)

:: ── 3. Generate icon ─────────────────────────────────────────────────
echo.
echo [3/4] Generating icon...
python create_icon.py
if ERRORLEVEL 1 (
    echo WARNING: Icon generation failed. Building without custom icon.
    set ICON_ARG=
) else (
    set ICON_ARG=--icon=assets\icon.ico
)

:: ── 4. PyInstaller build ─────────────────────────────────────────────
echo.
echo [4/4] Building executable...

pyinstaller ^
    --onefile ^
    --windowed ^
    --name ScreenshotBuffer ^
    %ICON_ARG% ^
    --add-data "assets;assets" ^
    --hidden-import=win32clipboard ^
    --hidden-import=win32con ^
    --hidden-import=pynput.keyboard._win32 ^
    --hidden-import=pynput.mouse._win32 ^
    main.py

if ERRORLEVEL 1 (
    echo ERROR: Build failed.
    pause & exit /b 1
)

echo.
echo ============================================================
echo  Build complete!
echo  Executable: dist\ScreenshotBuffer.exe
echo
echo  To run: double-click dist\ScreenshotBuffer.exe
echo  Look for the blue camera icon in the system tray.
echo ============================================================
pause
