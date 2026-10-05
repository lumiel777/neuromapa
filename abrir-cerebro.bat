@echo off
cd /d "%~dp0"
title Neuromapa
set "lanzar="
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul && set "lanzar=py -3"
if not defined lanzar python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul && set "lanzar=python"
if not defined lanzar (
    echo Neuromapa necesita Python 3.10 o superior: https://www.python.org/downloads/
    pause
    exit /b 1
)
%lanzar% servidor.py
if errorlevel 1 (
    echo.
    echo No se pudo abrir el cerebro. Fijate el mensaje de arriba.
    pause
    exit /b 1
)
