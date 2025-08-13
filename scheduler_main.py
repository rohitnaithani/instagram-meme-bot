import schedule
import time
import subprocess
import sys
import os
from datetime import datetime

def run_meme_fetcher():
    """Fetch fresh memes from Reddit"""
    print(f"🎯 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Running meme fetcher...")
    try:
        result = subprocess.run([sys.executable, "cloud_meme_fetcher.py"], 
                              capture_output=True, text=True, timeout=600)
        if result.returncode == 0:
            print("✅ Meme fetcher completed successfully")
        else:
            print(f"❌ Meme fetcher failed: {result.stderr}")
    except subprocess.TimeoutExpired:
        print("⏰ Meme fetcher timed out")
    except Exception as e:
        print(f"❌ Error running meme fetcher: {e}")

def run_instagram_uploader():
    """Upload one meme to Instagram"""
    print(f"📤 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Running Instagram uploader...")
    try:
        result = subprocess.run([sys.executable, "cloud_instagram_uploader.py"], 
                              capture_output=True, text=True, timeout=900)
        if result.returncode == 0:
            print("✅ Instagram upload completed successfully")
        else:
            print(f"❌ Instagram upload failed: {result.stderr}")
    except subprocess.TimeoutExpired:
        print("⏰ Instagram uploader timed out")
    except Exception as e:
        print(f"❌ Error running Instagram uploader: {e}")

def main():
    print("🚀 Instagram Meme Bot Scheduler Started!")
    print(f"⏰ Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Schedule meme fetching (daily at 2 AM)
    schedule.every().day.at("02:00").do(run_meme_fetcher)
    
    # Schedule Instagram posts (5 times daily)
    schedule.every().day.at("09:00").do(run_instagram_uploader)  # Morning
    schedule.every().day.at("13:00").do(run_instagram_uploader)  # Afternoon  
    schedule.every().day.at("17:00").do(run_instagram_uploader)  # Evening
    schedule.every().day.at("21:00").do(run_instagram_uploader)  # Night
    schedule.every().day.at("23:00").do(run_instagram_uploader)  # Late night
    
    print("📅 Scheduled jobs:")
    print("  • Daily meme fetch: 2:00 AM")
    print("  • Instagram posts: 9:00 AM, 1:00 PM, 5:00 PM, 9:00 PM, 11:00 PM")
    print("\n🔄 Bot is running... Press Ctrl+C to stop")
    
    # Keep the scheduler running
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            print("\n🛑 Scheduler stopped by user")
            break
        except Exception as e:
            print(f"❌ Scheduler error: {e}")
            print("⏳ Continuing in 5 minutes...")
            time.sleep(300)

if __name__ == "__main__":
    main()