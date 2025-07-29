@echo off
echo ==========================================
echo   AI Chat - Lightweight Node.js Setup
echo ==========================================
echo.

echo You're absolutely right about Docker being memory-heavy!
echo Docker: 2-4GB+ RAM vs Node.js: ~250MB RAM
echo.

echo Checking if Node.js is installed...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo Node.js is NOT installed yet.
    echo.
    echo QUICK SETUP STEPS:
    echo 1. Download Node.js LTS from: https://nodejs.org/
    echo 2. Install with default settings
    echo 3. Restart this terminal
    echo 4. Run this script again
    echo.
    echo After installation, we'll use only ~250MB RAM instead of 2-4GB!
    echo.
    echo Opening Node.js download page...
    start https://nodejs.org/
    echo.
    pause
    exit /b 0
)

echo Node.js is installed!
node --version
npm --version
echo.

echo Starting backend (if not already running)...
start "Backend" cmd /k "cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000"

echo Waiting for backend to start...
timeout /t 3 /nobreak >nul

echo.
echo Installing frontend dependencies...
cd frontend
echo This will download packages (~100MB, much less than Docker!)
npm install

if %errorlevel% neq 0 (
    echo.
    echo npm install failed. Make sure Node.js is properly installed.
    pause
    exit /b 1
)

echo.
echo Starting frontend development server...
echo.
echo ==========================================
echo   Your AI Chat App is starting!
echo ==========================================
echo.
echo   Frontend: http://localhost:3000
echo   Backend:  http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo.
echo   Memory usage: ~250MB (vs 2-4GB with Docker!)
echo.
echo ==========================================

npm start
