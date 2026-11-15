@echo off
setlocal
title Tat UniStudy AI

cd /d "%~dp0"

echo ==============================================================
echo          UniStudy AI - Dung Ung Dung
echo ==============================================================
echo.
echo [*] Dang tat cac tien trinh may chu UniStudy AI - Port 8000, 5173...

rem 1. Dong tien trinh dang chiem port 8000 va 5173
powershell -NoProfile -Command "$ports = 8000, 5173; foreach ($p in $ports) { $conns = Get-NetTCPConnection -LocalPort $p -ErrorAction SilentlyContinue; if ($conns) { foreach ($c in $conns) { Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue } } }" >nul 2>&1

rem 2. Quet du phong theo tieu de cua so
taskkill /F /FI "WINDOWTITLE eq UniStudy AI Backend Server*" >nul 2>&1

echo.
echo ==============================================================
echo  [OK] Da tat toan bo tien trinh cua UniStudy AI thanh cong!
echo  [OK] Cong 8000 va 5173 da duoc giai phong hoan toan.
echo ==============================================================
echo.
echo Cua so se tu dong dong sau 3 giay...
ping 127.0.0.1 -n 4 >nul
