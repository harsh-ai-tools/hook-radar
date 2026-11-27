@echo off
setlocal
title HookRadar installer
cd /d "%~dp0"
echo.
echo  ==============================================
echo    HookRadar installer  (made by Harsh Rajput)
echo    Free and local. Nothing is uploaded.
echo  ==============================================
echo.
set PY=
for %%V in (3.12 3.13 3.11 3.10) do if not defined PY ( py -%%V --version >nul 2>nul && set "PY=py -%%V" )
if not defined PY ( python -c "import sys; sys.exit(0 if (3,10) <= sys.version_info[:2] <= (3,13) else 1)" >nul 2>nul && set PY=python )
if not defined PY (
  echo [1/4] Python not found.
  choice /M "Install Python 3.12 with winget now"
  if errorlevel 2 ( echo Please install Python 3.10-3.13 from python.org and run this again. & pause & exit /b 1 )
  winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
  echo.
  echo Python installed. Close this window and double-click install.bat again to continue.
  pause
  exit /b 0
) else ( echo [1/4] Python found: %PY% )
%PY% -c "import sys; sys.exit(0 if (3,10) <= sys.version_info[:2] <= (3,13) else 1)" || ( echo HookRadar needs Python 3.10 to 3.13. Please install Python 3.12 from python.org. & pause & exit /b 1 )
where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo [2/4] ffmpeg not found.
  choice /M "Install ffmpeg with winget now"
  if errorlevel 2 ( echo Install ffmpeg manually, then run this again. & pause & exit /b 1 )
  winget install -e --id Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
  echo NOTE: ffmpeg is installed. It works in NEW windows, so the launcher will find it.
) else ( echo [2/4] ffmpeg found. )
echo [3/4] Installing HookRadar packages (first time takes a few minutes)...
%PY% -m venv .venv || ( echo Could not create virtual environment & pause & exit /b 1 )
call .venv\Scripts\python -m pip install --upgrade pip >nul
call .venv\Scripts\python -m pip install -r requirements.txt || ( echo Package install failed & pause & exit /b 1 )
set GPUFLAG=
if exist .venv\gpu.flag del .venv\gpu.flag
where nvidia-smi >nul 2>nul
if not errorlevel 1 (
  if /I "%~1"=="--gpu" ( set WANTGPU=1 ) else (
    choice /M "NVIDIA GPU found. Install GPU speed-up for speech-to-text (about 1 GB download)"
    if not errorlevel 2 set WANTGPU=1
  )
)
if defined WANTGPU (
  echo Installing GPU speed-up...
  call .venv\Scripts\python -m pip install -r requirements-gpu.txt && set "GPUFLAG= --gpu" || echo GPU speed-up failed: HookRadar will use the CPU.
)
echo [4/4] Connecting the AI team to Claude...
call .venv\Scripts\python radar.py connect
if not exist library\me mkdir library\me
if defined WANTGPU if "%GPUFLAG%"==" --gpu" ( echo gpu> .venv\gpu.flag )
call .venv\Scripts\python radar.py doctor
echo.
echo  Done! Double-click START_DASHBOARD.bat to start.
echo  Put your videos in library\me and competitors' videos in library\^<their name^>.
pause
