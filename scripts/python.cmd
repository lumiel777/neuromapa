@echo off
setlocal
set "NoDefaultCurrentDirectoryInExePath=1"
if not defined PYTHONIOENCODING set "PYTHONIOENCODING=utf-8"
set "avisar=0"
set "hook=%~1"
if "%~1"=="--avisar" set "avisar=1"
if "%avisar%"=="1" set "hook=%~2"
set "guardado=%CLAUDE_PLUGIN_DATA%\python.txt"
set "nombre="
if "%avisar%"=="0" if defined CLAUDE_PLUGIN_DATA if exist "%guardado%" set /p nombre=<"%guardado%"
if not "%nombre%"=="py" if not "%nombre%"=="python" set "nombre="
set "recordado=%nombre%"
:buscar
if not defined nombre py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul && set "nombre=py"
if not defined nombre python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul && set "nombre=python"
if not defined nombre if "%avisar%"=="1" echo {"systemMessage": "Neuromapa necesita Python 3.10 o m\u00e1s nuevo y no lo encontr\u00e9 (prob\u00e9 py y python). Instalalo desde https://www.python.org/downloads/ y abr\u00ed Claude Code de nuevo. Mientras tanto, sus hooks no hacen nada."}
if not defined nombre exit /b 0
if not defined recordado if defined CLAUDE_PLUGIN_DATA mkdir "%CLAUDE_PLUGIN_DATA%" >nul 2>nul
if not defined recordado if defined CLAUDE_PLUGIN_DATA >"%guardado%" echo %nombre%
set "lanzar=python"
if "%nombre%"=="py" set "lanzar=py -3"
%lanzar% -I -S "%~dp0..\%hook%"
if not "%errorlevel%"=="9009" if not "%errorlevel%"=="103" exit /b
if not defined recordado exit /b
set "nombre="
set "recordado="
goto buscar
