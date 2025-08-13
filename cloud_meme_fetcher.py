import os
import praw
import requests
import json
from urllib.parse import urlparse
import time
import random

# ====== CONFIG FROM ENVIRONMENT VARIABLES ======
CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
USERNAME = os.getenv("REDDIT_USERNAME")
PASSWORD = os.getenv("REDDIT_PASSWORD")
USER_AGENT = f"meme-fetcher by u/{USERNAME}"

SUBREDDIT = "dankmemes"
IMAGES_TO_FETCH = 20
VIDEOS_TO_FETCH = 20
SAVE_FOLDER = "memes"
HISTORY_FILE = "downloaded.json"

# Create folders
os.makedirs(f"{SAVE_FOLDER}/images", exist_ok=True)
os.makedirs(f"{SAVE_FOLDER}/videos", exist_ok=True)

def load_history():
    """Load previously downloaded post IDs"""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    return {"downloaded_ids": [], "failed_urls": []}

def save_history(history):
    """Save downloaded post IDs to prevent duplicates"""
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

def get_valid_filename(title, post_id):
    """Create valid filename from post title"""
    valid_chars = "-_.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    filename = ''.join(c for c in title if c in valid_chars)
    filename = filename.replace(' ', '_')[:50]
    return f"{post_id}_{filename}"

def download_file(url, filepath, retries=3):
    """Download file with retry mechanism"""
    for attempt in range(retries):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"✅ Downloaded: {os.path.basename(filepath)}")
            return True
            
        except Exception as e:
            print(f"❌ Attempt {attempt + 1} failed for {url}: {e}")
            if attempt < retries - 1:
                time.sleep(2)
            
    return False

def fetch_memes():
    """Main function to fetch memes from Reddit"""
    print(f"🚀 Starting meme fetch from r/{SUBREDDIT}...")
    
    # Check environment variables
    if not all([CLIENT_ID, CLIENT_SECRET, USERNAME, PASSWORD]):
        print("❌ Missing environment variables! Check REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD")
        return
    
    # Load history
    history = load_history()
    downloaded_ids = set(history["downloaded_ids"])
    failed_urls = set(history["failed_urls"])
    
    # Initialize Reddit client
    try:
        reddit = praw.Reddit(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            username=USERNAME,
            password=PASSWORD,
            user_agent=USER_AGENT
        )
        print("✅ Connected to Reddit API")
    except Exception as e:
        print(f"❌ Failed to connect to Reddit: {e}")
        return
    
    image_count = 0
    video_count = 0
    processed = 0
    
    # Fetch posts from hot section
    try:
        for submission in reddit.subreddit(SUBREDDIT).hot(limit=300):
            processed += 1
            
            # Skip if already downloaded
            if submission.id in downloaded_ids:
                continue
                
            # Skip if previously failed
            if submission.url in failed_urls:
                continue
            
            # Process images
            if (submission.url.endswith(('.jpg', '.jpeg', '.png')) and 
                image_count < IMAGES_TO_FETCH):
                
                filename = get_valid_filename(submission.title, submission.id)
                filepath = os.path.join(SAVE_FOLDER, "images", f"{filename}.jpg")
                
                if download_file(submission.url, filepath):
                    image_count += 1
                    downloaded_ids.add(submission.id)
                else:
                    failed_urls.add(submission.url)
            
            # Process videos
            elif (("v.redd.it" in submission.url or submission.url.endswith('.mp4')) and 
                  video_count < VIDEOS_TO_FETCH):
                
                video_url = None
                
                # Handle Reddit videos
                if submission.media and "reddit_video" in submission.media:
                    video_url = submission.media["reddit_video"]["fallback_url"]
                elif submission.url.endswith('.mp4'):
                    video_url = submission.url
                
                if video_url:
                    filename = get_valid_filename(submission.title, submission.id)
                    filepath = os.path.join(SAVE_FOLDER, "videos", f"{filename}.mp4")
                    
                    if download_file(video_url, filepath):
                        video_count += 1
                        downloaded_ids.add(submission.id)
                    else:
                        failed_urls.add(submission.url)
            
            # Break if we have enough content
            if image_count >= IMAGES_TO_FETCH and video_count >= VIDEOS_TO_FETCH:
                break
                
            # Add small delay to be respectful to Reddit
            if processed % 10 == 0:
                time.sleep(1)
    
    except Exception as e:
        print(f"❌ Error fetching posts: {e}")
    
    # Save updated history
    history["downloaded_ids"] = list(downloaded_ids)
    history["failed_urls"] = list(failed_urls)
    save_history(history)
    
    print(f"\n🎯 Fetch Complete!")
    print(f"📸 Images downloaded: {image_count}/{IMAGES_TO_FETCH}")
    print(f"🎥 Videos downloaded: {video_count}/{VIDEOS_TO_FETCH}")
    print(f"📊 Posts processed: {processed}")
    print(f"💾 Total items in history: {len(downloaded_ids)}")

if __name__ == "__main__":
    fetch_memes()