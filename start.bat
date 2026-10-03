@echo off
REM ==========================================
REM    Phishy Platform - Unified Startup
REM ==========================================

cd /d "%~dp0"

REM Check if user wants ngrok (for Chrome extension)
echo.
echo Do you want to start with ngrok tunnel?
echo (Required for Chrome Extension to work)
echo.
echo [Y] Yes - Start with ngrok (for Chrome Extension)
echo [N] No  - Start locally only
echo.
choice /c YN /n /m "Your choice: "

if errorlevel 2 goto LOCAL
if errorlevel 1 goto NGROK

:NGROK
echo.
echo =========================================
echo    Starting Phishy with ngrok
echo =========================================
echo.

REM Check multiple ngrok locations
set "NGROK_PATH="

REM Check if ngrok is in PATH
where ngrok >nul 2>&1
if %errorlevel% equ 0 (
    set "NGROK_PATH=ngrok"
    goto NGROK_FOUND
)

REM Check common installation locations
if exist "%LOCALAPPDATA%\Microsoft\WindowsApps\ngrok.exe" (
    set "NGROK_PATH=%LOCALAPPDATA%\Microsoft\WindowsApps\ngrok.exe"
    goto NGROK_FOUND
)

if exist "C:\ngrok\ngrok.exe" (
    set "NGROK_PATH=C:\ngrok\ngrok.exe"
    goto NGROK_FOUND
)

if exist "%PROGRAMFILES%\ngrok\ngrok.exe" (
    set "NGROK_PATH=%PROGRAMFILES%\ngrok\ngrok.exe"
    goto NGROK_FOUND
)

if exist "%USERPROFILE%\ngrok.exe" (
    set "NGROK_PATH=%USERPROFILE%\ngrok.exe"
    goto NGROK_FOUND
)

if exist "%CD%\ngrok.exe" (
    set "NGROK_PATH=%CD%\ngrok.exe"
    goto NGROK_FOUND
)

REM ngrok not found - offer to help install
echo.
echo ========================================
echo   ERROR: ngrok not found!
echo ========================================
echo.
echo ngrok is required for the Chrome Extension to work.
echo.
echo How to install ngrok:
echo.
echo Option 1 - Quick Install (Recommended):
echo   1. Download: https://ngrok.com/download
echo   2. Extract ngrok.exe to: C:\Users\thoma\Desktop\Phishy\
echo   3. Run this script again
echo.
echo Option 2 - Add to PATH:
echo   1. Download from: https://ngrok.com/download
echo   2. Extract to a folder (e.g., C:\ngrok\)
echo   3. Add that folder to your Windows PATH
echo.
echo Option 3 - Windows Package Manager:
echo   winget install ngrok
echo.
echo Once installed, run this script again!
echo.
pause
exit /b 1

:NGROK_FOUND
echo Found ngrok at: %NGROK_PATH%

REM Check/create venv
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate and install deps
call venv\Scripts\activate.bat
python -c "import fastapi" 2>nul || (
    echo Installing dependencies...
    cd backend
    pip install -q -r requirements.txt
    cd ..
)

REM Start backend
echo Starting backend on port 8080...
start /min cmd /c "title Phishy-Backend && call venv\Scripts\activate.bat && cd backend && python app.py"

timeout /t 5 /nobreak >nul

REM Start ngrok tunnel (CORRECT PORT: 8080)
echo Starting ngrok tunnel on port 8080...
start "Phishy-ngrok" cmd /k ""%NGROK_PATH%" http 8080"

timeout /t 5 /nobreak >nul

REM Start frontend
echo Starting frontend on port 3001...
start /min cmd /c "title Phishy-Frontend && cd frontend && python -m http.server 3001"

timeout /t 2 /nobreak >nul

echo.
echo =========================================
echo    Phishy with ngrok is Running!
echo =========================================
echo.
echo   Frontend:  http://localhost:3001
echo   Backend:   http://localhost:8080
echo   API Docs:  http://localhost:8080/docs
echo   Ngrok UI:  http://127.0.0.1:4040
echo.
echo IMPORTANT: Get your ngrok URL
echo =========================================
echo 1. Look at the ngrok window that just opened
echo 2. Find the line "Forwarding"
echo 3. Copy the HTTPS URL (e.g., https://abc123.ngrok-free.app)
echo 4. Paste it into Chrome Extension settings
echo.
echo Example: https://1234-56-78-90.ngrok-free.app
echo.

REM Open ngrok dashboard
timeout /t 2 /nobreak >nul
start http://127.0.0.1:4040

REM Open frontend
timeout /t 2 /nobreak >nul
start http://localhost:3001

echo.
echo Press any key to STOP all servers...
pause >nul

REM Kill servers
echo Stopping servers...
taskkill /FI "WindowTitle eq Phishy-Backend" /F >nul 2>&1
taskkill /FI "WindowTitle eq Phishy-Frontend" /F >nul 2>&1
taskkill /FI "WindowTitle eq Phishy-ngrok" /F >nul 2>&1
taskkill /IM ngrok.exe /F >nul 2>&1
echo Servers stopped.
goto END

:LOCAL
echo.
echo =========================================
echo    Starting Phishy (Local Only)
echo =========================================
echo.
echo NOTE: Chrome Extension will NOT work in local mode!
echo      Use ngrok mode if you need the extension.
echo.

REM Check/create venv
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate venv and install deps
call venv\Scripts\activate.bat
python -c "import fastapi" 2>nul || (
    echo Installing dependencies...
    cd backend
    pip install -q -r requirements.txt
    cd ..
)

REM Start backend in background
echo Starting backend on port 8080...
start /min cmd /c "title Phishy-Backend && call venv\Scripts\activate.bat && cd backend && python app.py"

REM Wait for backend
timeout /t 5 /nobreak >nul

REM Start frontend in background
echo Starting frontend on port 3001...
start /min cmd /c "title Phishy-Frontend && cd frontend && python -m http.server 3001"

timeout /t 2 /nobreak >nul

echo.
echo =========================================
echo    Phishy is Running!
echo =========================================
echo.
echo   Frontend:  http://localhost:3001
echo   Backend:   http://localhost:8080
echo   API Docs:  http://localhost:8080/docs
echo.

REM Open browser
timeout /t 2 /nobreak >nul
start http://localhost:3001

echo.
echo Press any key to STOP all servers...
pause >nul

REM Kill servers
echo Stopping servers...
taskkill /FI "WindowTitle eq Phishy-Backend" /F >nul 2>&1
taskkill /FI "WindowTitle eq Phishy-Frontend" /F >nul 2>&1
echo Servers stopped.

:END
