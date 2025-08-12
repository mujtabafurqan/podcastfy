#!/usr/bin/env python3
"""
Railway-optimized web service for Podcastfy async API.
Standalone script that runs the FastAPI web server.
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set environment
os.environ.setdefault("PYTHONPATH", str(project_root))

try:
    # Import the async app
    from podcastfy.api.async_app import app
    
    if __name__ == "__main__":
        import uvicorn
        
        # Get port from environment (Railway sets this)
        port = int(os.environ.get("PORT", 8001))
        
        print(f"🚀 Starting Podcastfy API on port {port}")
        
        # Run with uvicorn
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            log_level="info"
        )
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("📁 Python path:", sys.path)
    print("📂 Current dir:", os.getcwd())
    print("📋 Directory contents:", os.listdir("."))
    sys.exit(1)
except Exception as e:
    print(f"💥 Startup error: {e}")
    sys.exit(1)