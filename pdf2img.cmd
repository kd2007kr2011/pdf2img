@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" pdf2img.py %*
) else (
  python pdf2img.py %*
)
pause
