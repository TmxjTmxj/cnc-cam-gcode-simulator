@echo off
cd /d %~dp0
where python >nul 2>nul
if %errorlevel%==0 (
    python -m PyInstaller --noconfirm --clean CNC_CAM_Simulator.spec
    goto :end
)
where py >nul 2>nul
if %errorlevel%==0 (
    py -m PyInstaller --noconfirm --clean CNC_CAM_Simulator.spec
    goto :end
)
echo Python 3.11+ command not found. Please install Python or add it to PATH.
pause
exit /b 1
:end
pause
