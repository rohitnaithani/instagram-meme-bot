import os
import praw
import requests
import json
from urllib.parse import urlparse
import time
import random
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('meme_fetcher.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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

def fetch_memes():
    # Debug info
    print(f"FETCH DEBUG - Current working directory: {os.getcwd()}")
    print(f"FETCH DEBUG - Memes directory exists: {os.path.exists('memes')}")
    
    # ... your existing meme fetching code

def diagnose_environment():
    """Diagnose environment setup and potential issues"""
    logger.info("🔍 Running diagnostic checks...")
    
    # Check environment variables
    env_vars = {
        "REDDIT_CLIENT_ID": CLIENT_ID,
        "REDDIT_CLIENT_SECRET": CLIENT_SECRET,
        "REDDIT_USERNAME": USERNAME,
        "REDDIT_PASSWORD": PASSWORD
    }
    
    missing_vars = []
    for var, value in env_vars.items():
        if not value:
            missing_vars.append(var)
            logger.error(f"❌ Missing environment variable: {var}")
        else:
            logger.info(f"✅ {var}: Set (length: {len(value)})")
    
    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    # Check folder permissions
    try:
        test_file = os.path.join(SAVE_FOLDER, "test.txt")
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        logger.info("✅ Write permissions: OK")
    except Exception as e:
        logger.error(f"❌ Write permission error: {e}")
        return False
    
    # Test internet connectivity
    try:
        response = requests.get("https://www.reddit.com", timeout=10)
        if response.status_code == 200:
            logger.info("✅ Internet connectivity: OK")
        else:
            logger.warning(f"⚠️  Reddit accessibility: HTTP {response.status_code}")
    except Exception as e:
        logger.error(f"❌ Internet connectivity error: {e}")
        return False
    
    return True

def test_reddit_connection():
    """Test Reddit API connection"""
    try:
        reddit = praw.Reddit(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            username=USERNAME,
            password=PASSWORD,
            user_agent=USER_AGENT
        )
        
        # Test authentication by getting user info
        user = reddit.user.me()
        logger.info(f"✅ Reddit authentication successful: {user.name}")
        
        # Test subreddit access
        subreddit = reddit.subreddit(SUBREDDIT)
        logger.info(f"✅ Subreddit access: r/{subreddit.display_name}")
        
        # Test fetching a few posts
        posts = list(subreddit.hot(limit=5))
        logger.info(f"✅ Successfully fetched {len(posts)} test posts")
        
        return reddit
        
    except Exception as e:
        logger.error(f"❌ Reddit connection failed: {e}")
        return None

def load_history():
    """Load previously downloaded post IDs"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                history = json.load(f)
                logger.info(f"📁 Loaded history: {len(history.get('downloaded_ids', []))} downloaded, {len(history.get('failed_urls', []))} failed")
                return history
        except Exception as e:
            logger.error(f"❌ Error loading history: {e}")
            return {"downloaded_ids": [], "failed_urls": []}
    return {"downloaded_ids": [], "failed_urls": []}

def save_history(history):
    """Save downloaded post IDs to prevent duplicates"""
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
        logger.info(f"💾 History saved: {len(history['downloaded_ids'])} total downloads")
    except Exception as e:
        logger.error(f"❌ Error saving history: {e}")

def get_valid_filename(title, post_id):
    """Create valid filename from post title"""
    valid_chars = "-_.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    filename = ''.join(c for c in title if c in valid_chars)
    filename = filename.replace(' ', '_')[:50]
    return f"{post_id}_{filename}"

def get_file_extension(url):
    """Get appropriate file extension from URL"""
    if url.endswith(('.jpg', '.jpeg')):
        return '.jpg'
    elif url.endswith('.png'):
        return '.png'
    elif url.endswith('.gif'):
        return '.gif'
    elif url.endswith('.mp4'):
        return '.mp4'
    else:
        # Default based on content type
        try:
            response = requests.head(url, timeout=5)
            content_type = response.headers.get('content-type', '')
            if 'image' in content_type:
                return '.jpg'
            elif 'video' in content_type:
                return '.mp4'
        except:
            pass
        return '.jpg'  # Default fallback

def download_file(url, filepath, retries=3):
    """Download file with retry mechanism and better error handling"""
    for attempt in range(retries):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            logger.info(f"📥 Downloading: {url}")
            response = requests.get(url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '')
            if not any(x in content_type for x in ['image', 'video', 'octet-stream']):
                logger.warning(f"⚠️  Unexpected content type: {content_type}")
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = os.path.getsize(filepath)
            if file_size < 1024:  # Less than 1KB might be an error page
                logger.warning(f"⚠️  Small file size: {file_size} bytes")
                os.remove(filepath)
                return False
            
            logger.info(f"✅ Downloaded: {os.path.basename(filepath)} ({file_size} bytes)")
            return True
            
        except Exception as e:
            logger.warning(f"❌ Attempt {attempt + 1} failed for {url}: {e}")
            if os.path.exists(filepath):
                os.remove(filepath)
            if attempt < retries - 1:
                time.sleep(random.uniform(2, 5))  # Random delay
            
    return False

def is_valid_image_url(url):
    """Check if URL points to a valid image"""
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif')
    image_domains = ['i.redd.it', 'preview.redd.it', 'i.imgur.com']
    
    return (url.endswith(image_extensions) or 
            any(domain in url for domain in image_domains))

def is_valid_video_url(url):
    """Check if URL points to a valid video"""
    return ("v.redd.it" in url or url.endswith('.mp4') or 
            "gfycat.com" in url or "redgifs.com" in url)

def fetch_memes():
    """Main function to fetch memes from Reddit"""
    start_time = time.time()
    logger.info(f"🚀 Starting enhanced meme fetch from r/{SUBREDDIT}...")
    
    # Run diagnostics
    if not diagnose_environment():
        logger.error("❌ Environment diagnostic failed. Exiting.")
        return
    
    # Test Reddit connection
    reddit = test_reddit_connection()
    if not reddit:
        logger.error("❌ Reddit connection failed. Exiting.")
        return
    
    # Load history
    history = load_history()
    downloaded_ids = set(history["downloaded_ids"])
    failed_urls = set(history["failed_urls"])
    
    image_count = 0
    video_count = 0
    processed = 0
    skipped = 0
    
    # Fetch posts from hot section
    try:
        subreddit = reddit.subreddit(SUBREDDIT)
        logger.info(f"📋 Fetching posts from r/{SUBREDDIT}...")
        
        for submission in subreddit.hot(limit=500):  # Increased limit
            processed += 1
            
            # Skip if already downloaded
            if submission.id in downloaded_ids:
                skipped += 1
                continue
                
            # Skip if previously failed
            if submission.url in failed_urls:
                skipped += 1
                continue
            
            # Skip deleted or removed posts
            if submission.removed_by_category or not submission.title:
                continue
            
            logger.info(f"🔍 Processing: {submission.title[:50]}...")
            
            # Process images
            if is_valid_image_url(submission.url) and image_count < IMAGES_TO_FETCH:
                filename = get_valid_filename(submission.title, submission.id)
                extension = get_file_extension(submission.url)
                filepath = os.path.join(SAVE_FOLDER, "images", f"{filename}{extension}")
                
                if download_file(submission.url, filepath):
                    image_count += 1
                    downloaded_ids.add(submission.id)
                    logger.info(f"📸 Image {image_count}/{IMAGES_TO_FETCH} downloaded")
                else:
                    failed_urls.add(submission.url)
            
            # Process videos
            elif is_valid_video_url(submission.url) and video_count < VIDEOS_TO_FETCH:
                video_url = None
                
                # Handle Reddit videos
                if hasattr(submission, 'media') and submission.media and "reddit_video" in submission.media:
                    video_url = submission.media["reddit_video"]["fallback_url"]
                elif submission.url.endswith('.mp4'):
                    video_url = submission.url
                elif "v.redd.it" in submission.url:
                    # Try to construct video URL
                    video_url = submission.url + "/DASH_720.mp4"
                
                if video_url:
                    filename = get_valid_filename(submission.title, submission.id)
                    filepath = os.path.join(SAVE_FOLDER, "videos", f"{filename}.mp4")
                    
                    if download_file(video_url, filepath):
                        video_count += 1
                        downloaded_ids.add(submission.id)
                        logger.info(f"🎥 Video {video_count}/{VIDEOS_TO_FETCH} downloaded")
                    else:
                        failed_urls.add(submission.url)
            
            # Break if we have enough content
            if image_count >= IMAGES_TO_FETCH and video_count >= VIDEOS_TO_FETCH:
                logger.info("✅ Target numbers reached!")
                break
                
            # Add respectful delays
            if processed % 10 == 0:
                logger.info(f"📊 Progress: {processed} processed, {image_count} images, {video_count} videos, {skipped} skipped")
                time.sleep(random.uniform(1, 3))
    
    except Exception as e:
        logger.error(f"❌ Error fetching posts: {e}")
    
    # Save updated history
    history["downloaded_ids"] = list(downloaded_ids)
    history["failed_urls"] = list(failed_urls)
    history["last_fetch"] = datetime.now().isoformat()
    save_history(history)
    
    # Final statistics
    elapsed_time = time.time() - start_time
    logger.info(f"\n🎯 Fetch Complete!")
    logger.info(f"📸 Images downloaded: {image_count}/{IMAGES_TO_FETCH}")
    logger.info(f"🎥 Videos downloaded: {video_count}/{VIDEOS_TO_FETCH}")
    logger.info(f"📊 Posts processed: {processed}")
    logger.info(f"⏭️  Posts skipped: {skipped}")
    logger.info(f"💾 Total items in history: {len(downloaded_ids)}")
    logger.info(f"⏱️  Time elapsed: {elapsed_time:.2f} seconds")
    
    # Check if we got any content
    if image_count == 0 and video_count == 0:
        logger.warning("⚠️  No content downloaded! Check subreddit availability and filters.")
    
    return {
        "images": image_count,
        "videos": video_count,
        "processed": processed,
        "time_elapsed": elapsed_time
    }

if __name__ == "__main__":
    fetch_memes()
