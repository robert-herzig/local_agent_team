@echo off
echo Starting AI Chat Application with Docker...
echo.

echo Checking if Docker is running...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not installed or not running.
    echo Please install Docker Desktop and make sure it's running.
    echo Download from: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

echo Docker detected. Building and starting services...
echo.

echo Building images (this may take a few minutes on first run)...
docker-compose -f docker-compose.dev.yml build

echo.
echo Starting services...
docker-compose -f docker-compose.dev.yml up -d

echo.
echo Waiting for services to start...
timeout /t 10 /nobreak >nul

echo.
echo ================================================================
echo  AI Chat Application is starting up!
echo ================================================================
echo.
echo  Frontend (React):  http://localhost:3000
echo  Backend API:       http://localhost:8000
echo  API Docs:          http://localhost:8000/docs
echo.
echo  The application may take a minute to fully load on first startup.
echo.
echo  To stop the application, run: docker-compose -f docker-compose.dev.yml down
echo  To view logs, run: docker-compose -f docker-compose.dev.yml logs -f
echo.
echo ================================================================

echo Opening application in browser...
start http://localhost:3000

echo.
echo Press any key to view logs, or close this window to continue...
pause >nul
docker-compose -f docker-compose.dev.yml logs -f
