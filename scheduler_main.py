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
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    
    # Keep last 50 log entries
    bot_status["recent_logs"].append(log_entry)
    if len(bot_status["recent_logs"]) > 50:
        bot_status["recent_logs"] = bot_status["recent_logs"][-50:]

def check_environment():
    """Check all environment variables"""
    required_vars = {
        "INSTAGRAM_USERNAME": os.getenv("INSTAGRAM_USERNAME"),
        "INSTAGRAM_PASSWORD": os.getenv("INSTAGRAM_PASSWORD"),
        "REDDIT_CLIENT_ID": os.getenv("REDDIT_CLIENT_ID"),
        "REDDIT_CLIENT_SECRET": os.getenv("REDDIT_CLIENT_SECRET"),
        "REDDIT_USERNAME": os.getenv("REDDIT_USERNAME"),
        "REDDIT_PASSWORD": os.getenv("REDDIT_PASSWORD")
    }
    
    env_status = {}
    missing_vars = []
    
    for var, value in required_vars.items():
        if value:
            env_status[var] = f"✅ Set (length: {len(value)})"
        else:
            env_status[var] = "❌ Missing"
            missing_vars.append(var)
    
    if missing_vars:
        log_message(f"❌ Missing environment variables: {', '.join(missing_vars)}")
    
    return env_status

def check_meme_files():
    """Check available meme files"""
    memes_folder = "memes"
    
    # Create folders if they don't exist
    os.makedirs(os.path.join(memes_folder, "images"), exist_ok=True)
    os.makedirs(os.path.join(memes_folder, "videos"), exist_ok=True)
    
    # Check images
    image_patterns = [
        os.path.join(memes_folder, "images", "*.jpg"),
        os.path.join(memes_folder, "images", "*.jpeg"), 
        os.path.join(memes_folder, "images", "*.png")
    ]
    
    image_files = []
    for pattern in image_patterns:
        image_files.extend(glob.glob(pattern))
    
    # Check videos
    video_patterns = [
        os.path.join(memes_folder, "videos", "*.mp4"),
        os.path.join(memes_folder, "videos", "*.mov")
    ]
    
    video_files = []
    for pattern in video_patterns:
        video_files.extend(glob.glob(pattern))
    
    return image_files, video_files

def update_bot_status():
    """Update global bot status"""
    global bot_status
    
    try:
        # Check environment
        bot_status["environment_check"] = check_environment()
        
        # Check files
        image_files, video_files = check_meme_files()
        bot_status["total_images"] = len(image_files)
        bot_status["total_videos"] = len(video_files)
        
        # Check upload state
        state_file = "upload_state.json"
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                bot_status["posted_count"] = len(state.get("posted_files", []))
                bot_status["last_upload"] = state.get("last_upload_date", "Never")
                
                # Calculate available files
                all_files = image_files + video_files
                posted_files = set(state.get("posted_files", []))
                available_files = [f for f in all_files if f not in posted_files]
                bot_status["available_count"] = len(available_files)
            except Exception as e:
                bot_status["errors"].append(f"State file error: {e}")
                log_message(f"State file error: {e}")
        else:
            bot_status["available_count"] = bot_status["total_images"] + bot_status["total_videos"]
            
        # Check fetch history
        history_file = "downloaded.json"
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r') as f:
                    history = json.load(f)
                downloaded_count = len(history.get("downloaded_ids", []))
                log_message(f"Total memes downloaded: {downloaded_count}")
            except Exception as e:
                log_message(f"History file error: {e}")
                
    except Exception as e:
        log_message(f"Error updating bot status: {e}")
        bot_status["errors"].append(f"Status update error: {e}")

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Update status before showing
        update_bot_status()
        
        if self.path == "/" or self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            
            # Environment status
            env_html = ""
            for var, status in bot_status["environment_check"].items():
                color = "green" if "✅" in status else "red"
                env_html += f"<tr><td>{var}</td><td style='color: {color}'>{status}</td></tr>"
            
            # Recent logs
            logs_html = ""
            for log in bot_status["recent_logs"][-10:]:  # Last 10 logs
                logs_html += f"<div style='font-family: monospace; font-size: 12px; margin: 2px 0;'>{log}</div>"
            
            # Diagnose issues
            diagnosis_html = self.get_diagnosis()
            
            # Main status HTML
            status_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Instagram Meme Bot - Render Dashboard</title>
                <meta http-equiv="refresh" content="30">
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
                    .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }}
                    .status-box {{ background: #e8f5e8; padding: 15px; margin: 10px 0; border-radius: 5px; }}
                    .error-box {{ background: #ffe6e6; padding: 15px; margin: 10px 0; border-radius: 5px; }}
                    .warning-box {{ background: #fff3cd; padding: 15px; margin: 10px 0; border-radius: 5px; }}
                    .button {{ display: inline-block; background: #4CAF50; color: white; padding: 10px 20px; 
                             text-decoration: none; border-radius: 5px; margin: 5px; }}
                    .button:hover {{ background: #45a049; }}
                    .debug-button {{ background: #2196F3; }}
                    .force-button {{ background: #ff9800; }}
                    .danger-button {{ background: #f44336; }}
                    table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    .logs {{ background: #f8f9fa; padding: 10px; border-radius: 5px; max-height: 300px; overflow-y: auto; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🤖 Instagram Meme Bot - Render Dashboard</h1>
                    <p><strong>Status:</strong> Running on Render | <strong>Updated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    
                    {diagnosis_html}
                    
                    <div class="status-box">
                        <h2>📊 Current Status</h2>
                        <table>
                            <tr><th>Metric</th><th>Value</th><th>Status</th></tr>
                            <tr><td>Total Images</td><td>{bot_status["total_images"]}</td><td>{'✅' if bot_status["total_images"] > 0 else '❌ No images'}</td></tr>
                            <tr><td>Total Videos</td><td>{bot_status["total_videos"]}</td><td>{'✅' if bot_status["total_videos"] > 0 else '⚠️ No videos'}</td></tr>
                            <tr><td>Files Posted</td><td>{bot_status["posted_count"]}</td><td>{'✅' if bot_status["posted_count"] > 0 else '❌ No posts yet'}</td></tr>
                            <tr><td>Files Available</td><td>{bot_status["available_count"]}</td><td>{'✅' if bot_status["available_count"] > 0 else '❌ Nothing to post'}</td></tr>
                            <tr><td>Last Fetch</td><td>{bot_status["last_fetch"]}</td><td>{'⚠️ Never ran' if bot_status["last_fetch"] == 'Never' else '✅'}</td></tr>
                            <tr><td>Last Upload</td><td>{bot_status["last_upload"]}</td><td>{'❌ Never uploaded' if bot_status["last_upload"] == 'Never' else '✅'}</td></tr>
                        </table>
                    </div>
                    
                    <div class="status-box">
                        <h2>🔧 Environment Variables</h2>
                        <table>
                            <tr><th>Variable</th><th>Status</th></tr>
                            {env_html}
                        </table>
                    </div>
                    
                    <div class="status-box">
                        <h2>🎮 Manual Controls</h2>
                        <a href="/force-fetch" class="button force-button">🔄 Force Meme Fetch</a>
                        <a href="/force-upload" class="button force-button">📤 Force Instagram Upload</a>
                        <a href="/reset-cycle" class="button danger-button">🔄 Reset Upload Cycle</a>
                        <a href="/debug-detailed" class="button debug-button">🔍 Detailed Debug</a>
                    </div>
                    
                    <div class="status-box">
                        <h2>📋 Recent Logs</h2>
                        <div class="logs">
                            {logs_html}
                        </div>
                    </div>
                    
                    <div class="status-box">
                        <h2>⏰ Next Scheduled Tasks</h2>
                        <p>📥 Next meme fetch: Daily at 2:00 AM</p>
                        <p>📤 Next uploads: 9:00 AM, 1:00 PM, 5:00 PM, 9:00 PM, 11:00 PM</p>
                    </div>
                    
                    <p style="text-align: center; color: #666; font-size: 12px;">
                        Auto-refreshes every 30 seconds | Running on Render
                    </p>
                </div>
            </body>
            </html>
            """
            self.wfile.write(status_html.encode())
            
        elif self.path == "/force-fetch":
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write("🔄 Starting forced meme fetch...\n".encode())
            threading.Thread(target=run_meme_fetcher, args=(True,), daemon=True).start()
            
        elif self.path == "/force-upload":
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write("📤 Starting forced Instagram upload...\n".encode())
            threading.Thread(target=run_instagram_uploader, args=(True,), daemon=True).start()
            
        elif self.path == "/reset-cycle":
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            try:
                if os.path.exists("upload_state.json"):
                    with open("upload_state.json", 'w') as f:
                        json.dump({"posted_files": [], "last_upload_date": ""}, f)
                    self.wfile.write("✅ Upload cycle reset! All files available again.\n".encode())
                    log_message("🔄 Upload cycle manually reset")
                else:
                    self.wfile.write("ℹ️ No upload state to reset.\n".encode())
            except Exception as e:
                self.wfile.write(f"❌ Error resetting cycle: {e}\n".encode())
                
        elif self.path == "/debug-detailed":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            debug_html = self.get_detailed_debug()
            self.wfile.write(debug_html.encode())
            
        else:
            self.send_response(404)
            self.end_headers()

    def get_diagnosis(self):
        """Get diagnosis of potential issues"""
        issues = []
        
        # Check for no content
        if bot_status["total_images"] == 0 and bot_status["total_videos"] == 0:
            issues.append("❌ <strong>No meme files found!</strong> The meme fetcher hasn't run successfully.")
        
        # Check for missing environment variables
        missing_vars = [var for var, status in bot_status["environment_check"].items() if "❌" in status]
        if missing_vars:
            issues.append(f"❌ <strong>Missing environment variables:</strong> {', '.join(missing_vars)}")
        
        # Check if nothing available to post
        if bot_status["available_count"] == 0 and bot_status["total_images"] + bot_status["total_videos"] > 0:
            issues.append("⚠️ <strong>All files have been posted.</strong> Cycle will reset automatically.")
        
        # Check if uploads never happened
        if bot_status["last_upload"] == "Never" and bot_status["available_count"] > 0:
            issues.append("❌ <strong>No uploads have occurred.</strong> Instagram login might be failing.")
        
        if not issues:
            return '<div class="status-box"><h2>✅ System Status: Good</h2><p>No major issues detected.</p></div>'
        
        issues_html = "<br>".join(issues)
        return f'<div class="error-box"><h2>🚨 Issues Detected</h2>{issues_html}</div>'
    
    def get_detailed_debug(self):
        """Get detailed debug information"""
        # File system check
        file_info = ""
        try:
            for root, dirs, files in os.walk("memes"):
                file_info += f"<p><strong>{root}:</strong> {len(files)} files</p>"
                for file in files[:5]:  # Show first 5 files
                    file_path = os.path.join(root, file)
                    size = os.path.getsize(file_path)
                    file_info += f"<p style='margin-left: 20px;'>- {file} ({size} bytes)</p>"
        except Exception as e:
            file_info = f"<p>Error reading files: {e}</p>"
        
        # State file info
        state_info = ""
        try:
            if os.path.exists("upload_state.json"):
                with open("upload_state.json", 'r') as f:
                    state = json.load(f)
                state_info = f"<pre>{json.dumps(state, indent=2)}</pre>"
            else:
                state_info = "<p>No upload state file found</p>"
        except Exception as e:
            state_info = f"<p>Error reading state: {e}</p>"
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head><title>Detailed Debug Info</title></head>
        <body style="font-family: Arial, sans-serif; margin: 20px;">
            <h1>🔍 Detailed Debug Information</h1>
            <a href="/" style="color: blue;">← Back to Dashboard</a>
            
            <h2>📁 File System</h2>
            {file_info}
            
            <h2>📊 Upload State</h2>
            {state_info}
            
            <h2>📋 All Recent Logs</h2>
            <div style="background: #f8f9fa; padding: 10px; font-family: monospace; font-size: 12px;">
                {'<br>'.join(bot_status["recent_logs"])}
            </div>
        </body>
        </html>
        """

def start_health_server():
    """Start health check server for Render"""
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    log_message(f"🌐 Dashboard server started on port {port}")
    server.serve_forever()

def run_meme_fetcher(force=False):
    """Fetch fresh memes from Reddit"""
    action = "Forced meme fetch" if force else "Scheduled meme fetch"
    log_message(f"🔄 Starting {action.lower()}...")
    
    try:
        result = subprocess.run([sys.executable, "cloud_meme_fetcher.py"], 
                              capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0:
            log_message("✅ Meme fetcher completed successfully")
            bot_status["last_fetch"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            # Parse output for more details
            if "Images downloaded:" in result.stdout:
                log_message(f"📸 {result.stdout.split('Images downloaded:')[1].split()[0]} images downloaded")
            if "Videos downloaded:" in result.stdout:
                log_message(f"🎥 {result.stdout.split('Videos downloaded:')[1].split()[0]} videos downloaded")
        else:
            error_msg = f"Meme fetcher failed: {result.stderr}"
            log_message(f"❌ {error_msg}")
            bot_status["errors"].append(error_msg)
            
    except subprocess.TimeoutExpired:
        error_msg = "Meme fetcher timed out (10 minutes)"
        log_message(f"⏰ {error_msg}")
        bot_status["errors"].append(error_msg)
    except Exception as e:
        error_msg = f"Error running meme fetcher: {e}"
        log_message(f"❌ {error_msg}")
        bot_status["errors"].append(error_msg)

def run_instagram_uploader(force=False):
    """Upload one meme to Instagram"""
    action = "Forced Instagram upload" if force else "Scheduled Instagram upload"
    log_message(f"📤 Starting {action.lower()}...")
    
    try:
        result = subprocess.run([sys.executable, "cloud_instagram_uploader.py"], 
                              capture_output=True, text=True, timeout=900)
        
        if result.returncode == 0:
            log_message("✅ Instagram upload completed successfully")
            bot_status["last_upload"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            # Check if actually posted
            if "Upload successful" in result.stdout:
                log_message("📱 Post confirmed on Instagram")
            elif "Login failed" in result.stdout:
                log_message("❌ Instagram login failed - check credentials")
        else:
            error_msg = f"Instagram upload failed: {result.stderr}"
            log_message(f"❌ {error_msg}")
            bot_status["errors"].append(error_msg)
            
    except subprocess.TimeoutExpired:
        error_msg = "Instagram uploader timed out (15 minutes)"
        log_message(f"⏰ {error_msg}")
        bot_status["errors"].append(error_msg)
    except Exception as e:
        error_msg = f"Error running Instagram uploader: {e}"
        log_message(f"❌ {error_msg}")
        bot_status["errors"].append(error_msg)

def main():
    log_message("🚀 Instagram Meme Bot Scheduler Started on Render!")
    log_message(f"🕐 Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initial status update
    update_bot_status()
    
    # Start health server in background thread
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    
    # Schedule meme fetching (daily at 2 AM)
    schedule.every().day.at("02:00").do(run_meme_fetcher)
    
    # Schedule Instagram posts (5 times daily)
    schedule.every().day.at("09:00").do(run_instagram_uploader)
    schedule.every().day.at("13:00").do(run_instagram_uploader)
    schedule.every().day.at("17:00").do(run_instagram_uploader)
    schedule.every().day.at("21:00").do(run_instagram_uploader)
    schedule.every().day.at("23:00").do(run_instagram_uploader)
    
    log_message("📅 Scheduled jobs configured:")
    log_message("   - Daily meme fetch: 2:00 AM")
    log_message("   - Instagram posts: 9:00 AM, 1:00 PM, 5:00 PM, 9:00 PM, 11:00 PM")
    log_message("🌐 Dashboard available at your Render URL")
    
    # Keep the scheduler running
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            log_message("🛑 Scheduler stopped by user")
            break
        except Exception as e:
            error_msg = f"Scheduler error: {e}"
            log_message(f"❌ {error_msg}")
            bot_status["errors"].append(error_msg)
            log_message("⏳ Continuing in 5 minutes...")
            time.sleep(300)

if __name__ == "__main__":
    main()
