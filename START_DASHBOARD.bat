@echo off
rem Double-click me to start Reel Radar.
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe ( echo Run INSTALL_WINDOWS.bat first. & pause & exit /b 1 )
if not exist radar.json .venv\Scripts\python radar.py init
set FLAG=
if exist .venv\gpu.flag set FLAG=--gpu
.venv\Scripts\python radar.py watch %FLAG% %*
pause
