import schedule
import time
import subprocess
import sys
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            
            # Show bot status
            status_html = f"""
            <html>
            <head><title>Instagram Meme Bot Status</title></head>
            <body>
                <h1>Instagram Meme Bot</h1>
                <p><strong>Status:</strong> Running</p>
                <p><strong>Current Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>Next Posts:</strong> 9:00 AM, 1:00 PM, 5:00 PM, 9:00 PM, 11:00 PM</p>
                <p><strong>Meme Fetch:</strong> Daily at 2:00 AM</p>
                
                <h2>Test Buttons</h2>
                <a href="/test-fetch" style="background: #4CAF50; color: white; padding: 10px; text-decoration: none; border-radius: 5px;">Test Meme Fetch</a>
                <a href="/test-upload" style="background: #2196F3; color: white; padding: 10px; text-decoration: none; border-radius: 5px; margin-left: 10px;">Test Instagram Upload</a>
            </body>
            </html>
            """
            self.wfile.write(status_html.encode())
            
        elif self.path == "/test-fetch":
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write("Running meme fetch test...\n".encode())
            
            # Run meme fetcher in background
            threading.Thread(target=run_meme_fetcher, daemon=True).start()
            
        elif self.path == "/test-upload":
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write("Running Instagram upload test...\n".encode())
            
            # Run Instagram uploader in background
            threading.Thread(target=run_instagram_uploader, daemon=True).start()
            
        else:
            # Default page
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write("<h1>Instagram Meme Bot is Running!</h1><p><a href='/health'>Check Status</a></p>".encode())

def start_health_server():
    """Start health check server for Render"""
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"Health server started on port {port}")
    server.serve_forever()

def run_meme_fetcher():
    """Fetch fresh memes from Reddit"""
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Running meme fetcher...")
    try:
        result = subprocess.run([sys.executable, "cloud_meme_fetcher.py"], 
                              capture_output=True, text=True, timeout=600)
        if result.returncode == 0:
            print("Meme fetcher completed successfully")
        else:
            print(f"Meme fetcher failed: {result.stderr}")
    except subprocess.TimeoutExpired:
        print("Meme fetcher timed out")
    except Exception as e:
        print(f"Error running meme fetcher: {e}")

def run_instagram_uploader():
    """Upload one meme to Instagram"""
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Running Instagram uploader...")
    try:
        result = subprocess.run([sys.executable, "cloud_instagram_uploader.py"], 
                              capture_output=True, text=True, timeout=900)
        if result.returncode == 0:
            print("Instagram upload completed successfully")
        else:
            print(f"Instagram upload failed: {result.stderr}")
    except subprocess.TimeoutExpired:
        print("Instagram uploader timed out")
    except Exception as e:
        print(f"Error running Instagram uploader: {e}")

def main():
    print("Instagram Meme Bot Scheduler Started!")
    print(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Start health server in background thread
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    
    # Schedule meme fetching (daily at 2 AM)
    schedule.every().day.at("02:00").do(run_meme_fetcher)
    
    # Schedule Instagram posts (5 times daily)
    schedule.every().day.at("09:00").do(run_instagram_uploader)  # Morning
    schedule.every().day.at("13:00").do(run_instagram_uploader)  # Afternoon  
    schedule.every().day.at("17:00").do(run_instagram_uploader)  # Evening
    schedule.every().day.at("21:00").do(run_instagram_uploader)  # Night
    schedule.every().day.at("23:00").do(run_instagram_uploader)  # Late night
    
    print("Scheduled jobs:")
    print("  - Daily meme fetch: 2:00 AM")
    print("  - Instagram posts: 9:00 AM, 1:00 PM, 5:00 PM, 9:00 PM, 11:00 PM")
    print("Health check available at: /health")
    print("\nBot is running... Press Ctrl+C to stop")
    
    # Keep the scheduler running
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            print("\nScheduler stopped by user")
            break
        except Exception as e:
            print(f"Scheduler error: {e}")
            print("Continuing in 5 minutes...")
            time.sleep(300)

if __name__ == "__main__":
    main()
