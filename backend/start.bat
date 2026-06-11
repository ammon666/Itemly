@echo off
:: 从 backend 目录启动时，转发到项目根目录的 start.bat
cd /d "%~dp0.."
call start.bat
