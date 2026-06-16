@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

cd /d "%~dp0"

echo ========================================
echo   Itemly 本地启动
echo ========================================
echo.

:: 优先使用 py 启动器，避免 Windows Store 的 python 占位符
set "PY=py -3"
%PY% --version >nul 2>&1
if errorlevel 1 (
    set "PY=python"
    python --version >nul 2>&1
    if errorlevel 1 (
        echo [错误] 未找到 Python，请安装 Python 3.8+ 并勾选 "Add to PATH"。
        pause
        exit /b 1
    )
)

for /f "delims=" %%v in ('%PY% --version 2^>^&1') do echo 使用: %%v
echo.

:: 检查虚拟环境是否完整（仅有 python.exe 不够，必须有 activate.bat）
set "VENV_OK=0"
if exist "venv\Scripts\activate.bat" if exist "venv\Scripts\python.exe" set "VENV_OK=1"

if "%VENV_OK%"=="0" (
    if exist "venv" (
        echo [提示] 检测到不完整或损坏的 venv，正在清理后重建...
        echo        若删除失败，请先关闭所有 Itemly 窗口再重试。
        rmdir /s /q "venv" 2>nul
        if exist "venv" (
            echo [错误] 无法删除 venv 目录，可能有进程占用。
            echo        请关闭本窗口及其他 Python 进程后，手动删除 venv 文件夹再运行。
            pause
            exit /b 1
        )
    )

    echo [1/3] 创建虚拟环境（首次约 1~3 分钟，请耐心等待）...
    %PY% -m venv venv
    if errorlevel 1 (
        echo [错误] 虚拟环境创建失败。
        pause
        exit /b 1
    )

    if not exist "venv\Scripts\activate.bat" (
        echo [错误] 虚拟环境创建不完整，缺少 activate.bat。
        echo        可尝试手动执行: py -3 -m venv venv
        pause
        exit /b 1
    )
    echo        虚拟环境创建完成。
) else (
    echo [1/3] 虚拟环境已就绪
)

echo [2/3] 安装 / 更新依赖（需要联网，请稍候）...
call "venv\Scripts\activate.bat"
python -m pip install --upgrade pip
pip install -r backend\requirements.txt
if errorlevel 1 (
    echo [错误] 依赖安装失败，请检查网络或代理设置。
    pause
    exit /b 1
)

echo [3/3] 启动服务...
echo.
echo   访问地址: http://localhost:9009
echo   默认账号: admin / admin123
echo   按 Ctrl+C 停止服务
echo.

set PORT=9009
set FLASK_DEBUG=true
cd backend
python app.py

pause
