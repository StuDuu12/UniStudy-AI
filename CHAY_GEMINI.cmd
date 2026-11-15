@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "PYTHON_EXE="
if not defined PYTHON_EXE if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" --version >nul 2>&1
    if !errorlevel! equ 0 set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
)
if not defined PYTHON_EXE if exist "D:\UniStuAI\Chatbot UniStuAI\Chatbot UniStuAI\.venv\Scripts\python.exe" (
    "D:\UniStuAI\Chatbot UniStuAI\Chatbot UniStuAI\.venv\Scripts\python.exe" --version >nul 2>&1
    if !errorlevel! equ 0 set "PYTHON_EXE=D:\UniStuAI\Chatbot UniStuAI\Chatbot UniStuAI\.venv\Scripts\python.exe"
)
if not defined PYTHON_EXE if exist "%APPDATA%\uv\python\cpython-3.11-windows-x86_64-none\python.exe" (
    "%APPDATA%\uv\python\cpython-3.11-windows-x86_64-none\python.exe" --version >nul 2>&1
    if !errorlevel! equ 0 set "PYTHON_EXE=%APPDATA%\uv\python\cpython-3.11-windows-x86_64-none\python.exe"
)
if not defined PYTHON_EXE (
    where python >nul 2>&1
    if !errorlevel! equ 0 (
        python --version >nul 2>&1
        if !errorlevel! equ 0 set "PYTHON_EXE=python"
    )
)

echo Mở trình duyệt tại http://127.0.0.1:8000
start http://127.0.0.1:8000
"!PYTHON_EXE!" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
pause
endlocal
