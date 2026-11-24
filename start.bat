@echo off
REM Start the GxP AI Use-Case Assistant. Double-click this file.
REM Optional: "start.bat nobrowser" starts the app without opening the browser.
title GxP AI Use-Case Assistant
cd /d "%~dp0"
set "PORT=8000"
set "URL=http://127.0.0.1:%PORT%"

if not exist ".venv\Scripts\python.exe" (
    echo [!] Python environment not found in .venv
    echo     Create it with:  python -m venv .venv  and  .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

if not exist "data\index\manifest.json" (
    echo [setup] No index yet: downloading sources and building the index, about 3 minutes...
    ".venv\Scripts\python.exe" scripts\download_sources.py
    ".venv\Scripts\python.exe" -m app.ingest.build_index
    if errorlevel 1 (
        echo [!] Index build failed, see the messages above.
        pause
        exit /b 1
    )
)

REM An older copy of the app may still hold the port (its window minimised or
REM forgotten). It keeps serving the code it was started with, and a new server
REM cannot bind the port, so check first.
set "OLDPID="
for /f "tokens=5" %%P in ('netstat -ano -p tcp ^| findstr /r /c:":%PORT% .*LISTENING"') do set "OLDPID=%%P"
if not defined OLDPID goto :start_server

set "OLDNAME="
for /f "tokens=1 delims=," %%N in ('tasklist /fi "pid eq %OLDPID%" /fo csv /nh') do set "OLDNAME=%%~N"
echo [!] Port %PORT% is already in use by process %OLDPID% (%OLDNAME%).
if /i not "%OLDNAME%"=="python.exe" (
    echo     That is not this app. Free port %PORT% and run start.bat again.
    pause
    exit /b 1
)
echo     Probably an older copy of this app; it keeps running the code it was started with.
choice /c RO /n /m "    Press R to restart it with the current code, or O to just open it: "
if errorlevel 2 (
    start "" "%URL%"
    exit /b 0
)
taskkill /pid %OLDPID% /t /f >nul
ping -n 3 127.0.0.1 >nul

:start_server
if /i "%~1"=="nobrowser" goto :run
REM Open the browser once the server answers (start-up takes several seconds).
start "" /b powershell -NoProfile -Command "for ($i = 0; $i -lt 120; $i++) { try { Invoke-WebRequest -UseBasicParsing '%URL%/api/health' -TimeoutSec 2 | Out-Null; Start-Process '%URL%'; break } catch { Start-Sleep -Seconds 1 } }"

:run
echo.
echo  GxP AI Use-Case Assistant
echo  Open %URL%   (close this window or press Ctrl+C to stop)
echo.
".venv\Scripts\python.exe" -m uvicorn app.main:app --port %PORT%
echo.
echo [!] The server stopped. If you see an error above, it explains why.
pause
