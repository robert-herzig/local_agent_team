#!/bin/bash

# AI Search Chat - Setup Script
echo "🚀 Setting up AI Search Chat Web Interface..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 16+ first."
    exit 1
fi

# Check if Python is installed
if ! command -v python &> /dev/null; then
    echo "❌ Python is not installed. Please install Python 3.8+ first."
    exit 1
fi

echo "✅ Prerequisites check passed"

# Setup Backend
echo "📦 Setting up backend..."
cd backend
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "✅ Backend dependencies installed"
else
    echo "❌ requirements.txt not found in backend directory"
    exit 1
fi

# Setup Frontend
echo "📦 Setting up frontend..."
cd ../frontend
if [ -f "package.json" ]; then
    npm install
    echo "✅ Frontend dependencies installed"
else
    echo "❌ package.json not found in frontend directory"
    exit 1
fi

cd ..

echo "🎉 Setup complete!"
echo ""
echo "🚀 To start the application:"
echo "1. Start the backend: cd backend && python main.py"
echo "2. Start the frontend: cd frontend && npm start"
echo ""
echo "📱 Frontend will be available at: http://localhost:3000"
echo "🔧 Backend API will be available at: http://localhost:8000"
echo ""
echo "📖 For more information, see README.md"
