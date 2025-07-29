@echo off
REM AI Search Chat - Setup Script for Windows
echo 🚀 Setting up AI Search Chat Web Interface...

REM Check if Node.js is installed
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Node.js is not installed. Please install Node.js 16+ first.
    pause
    exit /b 1
)

REM Check if Python is installed
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Python is not installed. Please install Python 3.8+ first.
    pause
    exit /b 1
)

echo ✅ Prerequisites check passed

REM Setup Backend
echo 📦 Setting up backend...
cd backend
if exist requirements.txt (
    pip install -r requirements.txt
    echo ✅ Backend dependencies installed
) else (
    echo ❌ requirements.txt not found in backend directory
    pause
    exit /b 1
)

REM Setup Frontend
echo 📦 Setting up frontend...
cd ..\frontend
if exist package.json (
    npm install
    echo ✅ Frontend dependencies installed
) else (
    echo ❌ package.json not found in frontend directory
    pause
    exit /b 1
)

cd ..

echo 🎉 Setup complete!
echo.
echo 🚀 To start the application:
echo 1. Start the backend: cd backend ^&^& python main.py
echo 2. Start the frontend: cd frontend ^&^& npm start
echo.
echo 📱 Frontend will be available at: http://localhost:3000
echo 🔧 Backend API will be available at: http://localhost:8000
echo.
echo 📖 For more information, see README.md

pause
