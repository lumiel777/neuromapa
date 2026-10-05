@echo off
setlocal
set "NoDefaultCurrentDirectoryInExePath=1"
if not defined PYTHONIOENCODING set "PYTHONIOENCODING=utf-8"
set "lanzar="
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul && set "lanzar=py -3"
if not defined lanzar python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul && set "lanzar=python"
if not defined lanzar echo Neuromapa necesita Python 3.10 o superior: https://www.python.org/downloads/
if not defined lanzar exit /b 1
%lanzar% "%~dp0..\neuromapa.py" %*
exit /b %errorlevel%
