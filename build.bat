@echo off
chcp 65001 >nul
echo ============================================
echo Hebrew Subtitle Pipeline - Build Script
echo ============================================
echo.

REM Change to the script's directory
cd /d "%~dp0"
echo Working directory: %CD%
echo.

REM Check if Python is available
where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    pause
    exit /b 1
)

echo Installing dependencies...
python -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo Building executable...
python -m PyInstaller --clean "%~dp0subtitle_pipeline.spec"
if errorlevel 1 (
    echo ERROR: PyInstaller build failed
    pause
    exit /b 1
)

echo.
echo ============================================
echo Build complete!
echo Executable: %~dp0dist\HebrewSubtitlePipeline.exe
echo ============================================
pause
