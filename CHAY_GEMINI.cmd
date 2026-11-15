@echo off
setlocal
set "UNISTUDY_AI_ENDPOINT="
set "UNISTUDY_AI_MODEL="
set "UNISTUDY_AI_API_KEY="
cd /d "%~dp0" || exit /b 1
if not exist ".venv\Scripts\python.exe" (
    echo Tao moi truong Python theo README.md truoc khi chay.
    exit /b 1
)
".venv\Scripts\python.exe" -c "from pathlib import Path; from backend.services.llm_service import AIConfig; raise SystemExit(0 if AIConfig.load(Path('.env')) else 1)"
if errorlevel 1 (
    echo Dien endpoint, model va khoa API Gemini trong .env theo .env.example.
    exit /b 1
)
call "%~dp0CHAY_RAG.cmd"
exit /b %errorlevel%
