# Add these imports at the top
import threading
from meme_graphql import app as graphql_app
import uvicorn
import schedule
import time
import subprocess
import sys
import os
import threading
import json
import glob
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime


# Add this function after your existing functions
def start_graphql_server():
    """Start GraphQL server alongside existing dashboard"""
    graphql_port = int(os.environ.get("GRAPHQL_PORT", 8080))
    logger.info(f"🚀 Starting GraphQL server on port {graphql_port}")
    uvicorn.run(graphql_app, host="0.0.0.0", port=graphql_port)

# In your main() function, add this after starting the health server:
def main():
    # Your existing code...
    
    # Start health server (keep this)
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    
    # NEW: Start GraphQL server
    graphql_thread = threading.Thread(target=start_graphql_server, daemon=True)
    graphql_thread.start()
    
    # Rest of your existing code...

# Global status variables
bot_status = {
"last_fetch": "Never",
"last_upload": "Never", 
"total_images": 0,
"total_videos": 0,
"posted_count": 0,
"available_count": 0,
"errors": [],
"environment_check": {},
"recent_logs": []
}

def run_debug_check():
    """Run comprehensive debug check"""
    log_message("🔍 Running debug diagnostics...")
    try:
        result = subprocess.run([sys.executable, "cloud_instagram_uploader.py"], 
                              capture_output=True, text=True, timeout=300)
        
        # Log all output for debugging
        log_message("STDOUT:", result.stdout)
        log_message("STDERR:", result.stderr)
        log_message(f"Return code: {result.returncode}")
        
    except Exception as e:
        log_message(f"❌ Debug check failed: {e}")

def log_message(message):
"""Log message with timestamp"""
timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
