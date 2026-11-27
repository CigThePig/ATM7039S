@echo off
rem ATM7039S hardware test lab. Double-click this file to start.
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
set "PYEXE="
rem Prefer a Python version the lab is tested with; the newest Python may be too new for its libraries.
for %%v in (3.13 3.12 3.11) do (
  if not defined PYEXE (
    py -%%v -c "import sys" >nul 2>nul && set "PYEXE=py -%%v"
  )
)
if not defined PYEXE (
  where python >nul 2>nul && set "PYEXE=python"
)
if not defined PYEXE (
  echo Python was not found. Install Python 3.12 from https://www.python.org/downloads/
  echo and tick "Add python.exe to PATH". Then double-click this file again.
  pause
  exit /b 2
)
%PYEXE% "tools\lab_launch.py" %*
set "RC=%errorlevel%"
if not "%RC%"=="0" (
  echo.
  echo The lab stopped with a problem. The message above says what to do.
  pause
)
exit /b %RC%
