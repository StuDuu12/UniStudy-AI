@echo off
setlocal
cd /d "%~dp0" || exit /b 1
if not exist ".venv\Scripts\python.exe" (
    echo Tao moi truong Python theo README.md truoc khi chay.
    exit /b 1
)
if not exist "frontend\dist\index.html" (
    echo Chay npm run build trong thu muc frontend truoc.
    exit /b 1
)
".venv\Scripts\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
exit /b %errorlevel%
