@echo off
setlocal
set "UNISTUDY_AI_ENDPOINT=disabled"
call "%~dp0CHAY_RAG.cmd"
exit /b %errorlevel%
