@echo off
setlocal enabledelayedexpansion
title UniStudy AI Launcher

cd /d "%~dp0"

echo ==============================================================
echo          UniStudy AI - Tro Ly Hoc Tap Thong Minh
echo ==============================================================
echo.

rem 1. Xac dinh duong dan Python trong thu muc du an hoac he thong (kiem tra thuc thi hop le)
set "PYTHON_EXE="

rem Uu tien 1: Moi truong ao .venv tai thu muc du an
if not defined PYTHON_EXE (
    if exist "%~dp0.venv\Scripts\python.exe" (
        "%~dp0.venv\Scripts\python.exe" --version >nul 2>&1
        if !errorlevel! equ 0 (
            set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
        )
    )
)

rem Uu tien 2: Moi truong ao .venv tu thu muc anh em / du phong
if not defined PYTHON_EXE (
    for %%D in (
        "D:\UniStuAI\Chatbot UniStuAI\Chatbot UniStuAI\.venv\Scripts\python.exe"
        "D:\V3 chatbot\Chatbot UniStuAI\Chatbot UniStuAI\.venv\Scripts\python.exe"
    ) do (
        if not defined PYTHON_EXE (
            if exist %%D (
                %%D --version >nul 2>&1
                if !errorlevel! equ 0 (
                    set "PYTHON_EXE=%%~fD"
                )
            )
        )
    )
)

rem Uu tien 3: Python 3.11 do uv quan ly
if not defined PYTHON_EXE (
    if exist "%APPDATA%\uv\python\cpython-3.11-windows-x86_64-none\python.exe" (
        "%APPDATA%\uv\python\cpython-3.11-windows-x86_64-none\python.exe" --version >nul 2>&1
        if !errorlevel! equ 0 (
            set "PYTHON_EXE=%APPDATA%\uv\python\cpython-3.11-windows-x86_64-none\python.exe"
        )
    )
)

rem Uu tien 4: Trinh khoi chay py launcher (py -3.11 hoac py mac dinh)
if not defined PYTHON_EXE (
    where py >nul 2>&1
    if !errorlevel! equ 0 (
        for /f "delims=" %%I in ('py -3.11 -c "import sys; print(sys.executable)" 2^>nul') do (
            if not defined PYTHON_EXE (
                "%%I" --version >nul 2>&1
                if !errorlevel! equ 0 set "PYTHON_EXE=%%I"
            )
        )
        if not defined PYTHON_EXE (
            for /f "delims=" %%I in ('py -c "import sys; print(sys.executable)" 2^>nul') do (
                if not defined PYTHON_EXE (
                    "%%I" --version >nul 2>&1
                    if !errorlevel! equ 0 set "PYTHON_EXE=%%I"
                )
            )
        )
    )
)

rem Uu tien 5: System Python tren bien moi truong PATH
if not defined PYTHON_EXE (
    where python >nul 2>&1
    if !errorlevel! equ 0 (
        for /f "delims=" %%I in ('where python 2^>nul') do (
            if not defined PYTHON_EXE (
                "%%I" --version >nul 2>&1
                if !errorlevel! equ 0 (
                    set "PYTHON_EXE=%%I"
                )
            )
        )
    )
)

rem Uu tien 6: Cac duong dan cai dat Python pho bien tren Windows
if not defined PYTHON_EXE (
    for %%P in (
        "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
        "C:\Program Files\Python311\python.exe"
        "C:\Program Files\Python312\python.exe"
        "C:\Program Files\Python313\python.exe"
    ) do (
        if not defined PYTHON_EXE (
            if exist %%P (
                %%P --version >nul 2>&1
                if !errorlevel! equ 0 set "PYTHON_EXE=%%~fP"
            )
        )
    )
)

if not defined PYTHON_EXE (
    echo [LOI] Khong tim thay moi truong Python kha dung tren may!
    echo Vui long cai dat Python 3.11 hoac tao moi truong ao .venv tai thu muc du an.
    echo.
    pause
    exit /b 1
)

echo [*] Su dung Python: !PYTHON_EXE!
for /f "delims=" %%V in ('"!PYTHON_EXE!" --version 2^>^&1') do echo [*] Phien ban: %%V
echo.

rem Khoi dong Ollama va nap model song song voi backend.
start "UniStudy AI Ollama" /b "!PYTHON_EXE!" "%~dp0scripts\warm_ollama.py"

rem 2. Kiem tra xem port 8000 da co tien trinh nao chay chua
netstat -ano | findstr ":8000" | findstr "LISTENING" >nul 2>&1
if !errorlevel! equ 0 (
    echo [THONG BAO] May chu UniStudy AI da dang chay san tren cong 8000.
) else (
    echo [*] Dang khoi dong may chu UniStudy AI tren cong 8000...
    start "UniStudy AI Backend Server" cmd /k ""!PYTHON_EXE!" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"
    rem Doi 2 giay de may chu khoi dong hoan tat
    ping 127.0.0.1 -n 3 >nul
)

rem 3. Mo trinh duyet web
echo [*] Dang mo trinh duyet: http://127.0.0.1:8000 ...
start http://127.0.0.1:8000

echo.
echo ==============================================================
echo  [OK] UniStudy AI da san sang hoat dong!
echo  [OK] Dia chi web: http://127.0.0.1:8000
echo.
echo  - Ban co the thu nho cua so nay.
echo  - De dung chatbot khi khong dung nua, hay chay file:
echo    TAT_CHATBOT.cmd
echo ==============================================================
echo.
pause
