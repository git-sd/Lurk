@echo off
echo.
echo  ==========================================
echo   Lurk Setup - by Shreyan Das
echo  ==========================================
echo.

where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo  [ERROR] Python not found. Install Python 3.10+ from python.org
    pause
    exit /b 1
)

echo  Installing dependencies...
pip install -r requirements.txt --quiet

if %ERRORLEVEL% neq 0 (
    echo  [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo  Setup complete! Run Lurk with:
echo    python lurk.py
echo.
pause
