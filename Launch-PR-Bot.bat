@echo off
title PitchFlow Studio
echo ===================================================
echo   Starting PitchFlow Studio (Web Dashboard)
echo ===================================================
echo.
cd /d "%~dp0"
python main.py gui
pause
