@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

REM ==== video-voiceover-chatcut 依赖安装器 ====
set "MGR_PY=%USERPROFILE%\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
if exist "%MGR_PY%" (
  set "PY=%MGR_PY%"
) else (
  where python >nul 2>nul && set "PY=python"
)
if not defined PY (
  echo [ERROR] 没找到 Python。请先安装 Python 3.11+ 并加入 PATH，或安装 WorkBuddy。
  pause
  exit /b 1
)

"%PY%" "%~dp0setup.py"
echo.
pause
endlocal
