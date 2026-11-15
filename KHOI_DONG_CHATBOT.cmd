@echo off
setlocal
cd /d "%~dp0" || exit /b 1
set "APP_URL=http://127.0.0.1:8000/"

if /i "%~1"=="--wait-for-app" goto wait_for_app

call :open_if_ready
if not errorlevel 1 exit /b 0

if exist ".venv\Scripts\python.exe" if exist "frontend\dist\index.html" (
    echo Dang khoi dong UniStudy AI. Nhan Ctrl+C de dung.
    start "" /b "%ComSpec%" /d /c call "%~f0" --wait-for-app
)
call "%~dp0CHAY_RAG.cmd"
set "APP_EXIT_CODE=%ERRORLEVEL%"
if %APP_EXIT_CODE% GTR 0 pause
exit /b %APP_EXIT_CODE%

:wait_for_app
for /l %%i in (1,1,30) do (
    call :open_if_ready
    if not errorlevel 1 exit /b 0
    ping.exe -n 2 127.0.0.1 >nul
)
exit /b 1

:open_if_ready
curl.exe --silent --fail --noproxy "*" --max-time 1 "%APP_URL%" | findstr.exe /l /c:"<title>UniStudy AI" >nul
if errorlevel 1 exit /b 1
start "" "%APP_URL%"
exit /b 0
