@echo off
setlocal
cd /d "%~dp0"
set "UV_CACHE_DIR=%CD%\.uv-cache"
set "UV_PYTHON_DOWNLOADS=never"
uv run --locked ramtaskman %*
exit /b %errorlevel%
