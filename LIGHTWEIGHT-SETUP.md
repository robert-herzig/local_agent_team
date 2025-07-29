# Lightweight Setup Guide - Node.js Only

## 🚀 Quick Node.js Setup (Much Lighter than Docker!)

### Step 1: Install Node.js
1. Download Node.js LTS: https://nodejs.org/
2. Install with default settings
3. Restart your terminal/PowerShell

### Step 2: Install Frontend Dependencies
```bash
cd frontend
npm install
```

### Step 3: Start Both Services

**Terminal 1 (Backend - Already Running):**
Your FastAPI backend is already running on port 8000 ✅

**Terminal 2 (Frontend):**
```bash
cd frontend
npm start
```

### Memory Usage Comparison:
- **Docker**: 2-4GB+ RAM
- **Node.js**: ~200MB RAM
- **Your Backend**: ~50MB RAM

**Total with Node.js: ~250MB vs Docker: 2-4GB** 📈

### Why Node.js is Better Here:
✅ **Much less memory usage**
✅ **Faster startup time** 
✅ **Easier debugging**
✅ **Direct file editing** (no container rebuilding)
✅ **Simpler process management**

### Quick Test After Node.js Installation:
```bash
node --version
npm --version
```

If these work, you're ready to go! 🚀
