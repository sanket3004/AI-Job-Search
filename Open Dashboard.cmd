@echo off
setlocal
cd /d "%~dp0"
set "TOOLKIT_WORKSPACE=%~dp0job-search-workspace"
if not "%~1"=="" set "TOOLKIT_WORKSPACE=%~f1"
python -B "skills\ai-job-toolkit\scripts\toolkit.py" --workspace "%TOOLKIT_WORKSPACE%" init
if errorlevel 1 goto failed
python -B "skills\ai-job-toolkit\scripts\toolkit.py" --workspace "%TOOLKIT_WORKSPACE%" dashboard --open
if errorlevel 1 goto failed
exit /b 0
:failed
echo.
echo Dashboard could not start. Check the error above and that Python 3.10+ is available.
echo If port 8765 is in use, close the existing dashboard terminal or ask your AI to use a different port.
pause
exit /b 1
