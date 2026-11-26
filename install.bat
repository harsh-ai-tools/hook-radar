@echo off
setlocal
title Reel Radar installer
cd /d "%~dp0"
echo.
echo  ==============================================
echo    Reel Radar installer  (made by Harsh Rajput)
echo    Free and local. Nothing is uploaded.
echo  ==============================================
echo.
set PY=
where py >nul 2>nul && set PY=py -3
if not defined PY ( where python >nul 2>nul && set PY=python )
if not defined PY (
  echo [1/4] Python not found.
  choice /M "Install Python 3.12 with winget now"
  if errorlevel 2 ( echo Please install Python 3.10-3.13 from python.org and run this again. & pause & exit /b 1 )
  winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
  set PY=py -3
) else ( echo [1/4] Python found. )
where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo [2/4] ffmpeg not found.
  choice /M "Install ffmpeg with winget now"
  if errorlevel 2 ( echo Install ffmpeg manually, then run this again. & pause & exit /b 1 )
  winget install -e --id Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
  echo NOTE: close and reopen this window after installing ffmpeg if Reel Radar can't find it.
) else ( echo [2/4] ffmpeg found. )
echo [3/4] Installing Reel Radar packages (first time takes a few minutes)...
%PY% -m venv .venv || ( echo Could not create virtual environment & pause & exit /b 1 )
call .venv\Scripts\python -m pip install --upgrade pip >nul
call .venv\Scripts\python -m pip install -r requirements.txt || ( echo Package install failed & pause & exit /b 1 )
echo [4/4] Connecting the AI team to Claude...
call .venv\Scripts\python radar.py connect
> "Reel Radar.bat" echo @echo off
>> "Reel Radar.bat" echo cd /d "%%~dp0"
>> "Reel Radar.bat" echo if not exist radar.json ( .venv\Scripts\python radar.py init )
>> "Reel Radar.bat" echo .venv\Scripts\python radar.py watch %%*
>> "Reel Radar.bat" echo pause
echo.
echo  Done! Double-click "Reel Radar.bat" to start.
echo  Put videos you already have in library\me (yours) and library\^<creator^> (competitors).
pause
