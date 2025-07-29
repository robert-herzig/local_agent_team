# Node.js Setup Test and Guide
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Node.js Lightweight Setup Check" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Check if Node.js is installed
Write-Host "Test 1: Checking if Node.js is installed..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version 2>$null
    if ($nodeVersion) {
        Write-Host "✅ Node.js is installed!" -ForegroundColor Green
        Write-Host "   Version: $nodeVersion" -ForegroundColor Gray
        $nodeInstalled = $true
    } else {
        throw "Node.js not found"
    }
} catch {
    Write-Host "❌ Node.js not installed" -ForegroundColor Red
    $nodeInstalled = $false
}

Write-Host ""

# Test 2: Check if npm is available
if ($nodeInstalled) {
    Write-Host "Test 2: Checking if npm is available..." -ForegroundColor Yellow
    try {
        $npmVersion = npm --version 2>$null
        Write-Host "✅ npm is available!" -ForegroundColor Green
        Write-Host "   Version: $npmVersion" -ForegroundColor Gray
        $npmInstalled = $true
    } catch {
        Write-Host "❌ npm not available" -ForegroundColor Red
        $npmInstalled = $false
    }
} else {
    $npmInstalled = $false
}

Write-Host ""

# Test 3: Check if backend is still running
Write-Host "Test 3: Checking if backend is still running..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/" -Method GET -TimeoutSec 5
    Write-Host "✅ Backend is running!" -ForegroundColor Green
    $backendRunning = $true
} catch {
    Write-Host "❌ Backend not running" -ForegroundColor Red
    $backendRunning = $false
}

Write-Host ""

# Test 4: Check frontend directory and package.json
Write-Host "Test 4: Checking frontend setup..." -ForegroundColor Yellow
$frontendPath = "./frontend"
$packageJsonPath = "$frontendPath/package.json"

if (Test-Path $packageJsonPath) {
    Write-Host "✅ Frontend package.json found" -ForegroundColor Green
    $frontendReady = $true
} else {
    Write-Host "❌ Frontend package.json not found" -ForegroundColor Red
    $frontendReady = $false
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Setup Status Summary" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

if ($nodeInstalled -and $npmInstalled -and $backendRunning -and $frontendReady) {
    Write-Host "✅ EVERYTHING READY! You can start the frontend now!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Run these commands:" -ForegroundColor White
    Write-Host "cd frontend" -ForegroundColor Cyan
    Write-Host "npm install" -ForegroundColor Cyan
    Write-Host "npm start" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Your app will be available at:" -ForegroundColor White
    Write-Host "Frontend: http://localhost:3000" -ForegroundColor Cyan
    Write-Host "Backend:  http://localhost:8000" -ForegroundColor Cyan
} elseif ($backendRunning -and $frontendReady -and -not $nodeInstalled) {
    Write-Host "Need to install Node.js first:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "1. Download Node.js LTS from: https://nodejs.org/" -ForegroundColor White
    Write-Host "2. Install with default settings" -ForegroundColor White
    Write-Host "3. Restart PowerShell/Terminal" -ForegroundColor White
    Write-Host "4. Run this script again to verify" -ForegroundColor White
    Write-Host ""
    Write-Host "Memory usage comparison:" -ForegroundColor Cyan
    Write-Host "   Docker:  2-4GB+ RAM" -ForegroundColor Gray
    Write-Host "   Node.js: ~200MB RAM" -ForegroundColor Gray
    Write-Host "   Backend: ~50MB RAM" -ForegroundColor Gray
    Write-Host "   Total:   ~250MB (vs 2-4GB with Docker!)" -ForegroundColor Green
} else {
    Write-Host "⚠️  Some components need attention:" -ForegroundColor Yellow
    if (-not $backendRunning) {
        Write-Host "   - Start backend: cd backend && uvicorn main:app --reload" -ForegroundColor Gray
    }
    if (-not $frontendReady) {
        Write-Host "   - Frontend files may be missing" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "Memory-efficient setup is much better than Docker for development!" -ForegroundColor Green
Write-Host ""

Read-Host "Press Enter to continue..."
