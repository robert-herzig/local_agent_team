#!/usr/bin/env python3
"""
FastAPI Web Server Startup Script
"""
import os
import sys

# Make sure we're in the backend directory
backend_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(backend_dir)

# Add the backend directory to Python path
sys.path.insert(0, backend_dir)

# Import and start the server
if __name__ == "__main__":
    import uvicorn
    
    print("Starting FastAPI server from backend directory...")
    print(f"Working directory: {os.getcwd()}")
    
    # Import the app directly
    from main import app
    
    print("✓ FastAPI app imported successfully")
    print("🚀 Starting server on http://localhost:8000")
    
    uvicorn.run(
        app,  # Pass the app object directly
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable reload to avoid module loading issues
        log_level="info"
    )
