@echo off
rem ATM7039S hardware test lab. Double-click this file to start.
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "tools\lab_launch.py" %*
) else (
  python "tools\lab_launch.py" %*
)
if errorlevel 1 (
  echo.
  echo The lab stopped with a problem. The message above says what to do.
  pause
)
