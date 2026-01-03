@echo off
chcp 65001 >nul
echo Hebrew Subtitle Pipeline
echo ========================
echo.

if "%~1"=="" (
    echo Usage: run_pipeline.bat "path\to\season\folder"
    echo.
    echo Example: run_pipeline.bat "G:\Shows\ER\Season 6"
    pause
    exit /b 1
)

python "%~dp0src\main.py" %*
pause
