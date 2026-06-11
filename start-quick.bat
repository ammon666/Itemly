@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo   Itemly 快速启动（不使用虚拟环境）
echo ========================================
echo.

set "PY=py -3"
%PY% --version >nul 2>&1
if errorlevel 1 set "PY=python"

for /f "delims=" %%v in ('%PY% --version 2^>^&1') do echo 使用: %%v
echo.

echo 安装依赖...
%PY% -m pip install -r backend\requirements.txt
if errorlevel 1 (
    echo [错误] 依赖安装失败。
    pause
    exit /b 1
)

echo.
echo 启动服务: http://localhost:5000
echo 默认账号: admin / admin123
echo.

set PORT=5000
set FLASK_DEBUG=true
cd backend
%PY% app.py

pause
