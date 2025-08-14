import os
import praw
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
import tempfile
import time
import random
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ====== CONFIG FROM ENVIRONMENT VARIABLES ======
CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
USERNAME = os.getenv("REDDIT_USERNAME")
PASSWORD = os.getenv("REDDIT_PASSWORD")
USER_AGENT = f"meme-fetcher by u/{USERNAME}"

# Railway Database Connection
DATABASE_URL = os.getenv("DATABASE_URL")

SUBREDDIT = "dankmemes"
IMAGES_TO_FETCH = 20
VIDEOS_TO_FETCH = 5  # Reduced for free tier

class MemeDatabase:
    def __init__(self, database_url):
        self.database_url = database_url
        self.init_database()
    
    def get_connection(self):
        return psycopg2.connect(self.database_url)
    
    def init_database(self):
        """Initialize database tables"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS memes (
                            id SERIAL PRIMARY KEY,
                            post_id VARCHAR(50) UNIQUE,
                            title TEXT,
                            url TEXT,
                            file_type VARCHAR(10),
                            file_size INTEGER DEFAULT 0,
                            subreddit VARCHAR(50),
                            score INTEGER DEFAULT 0,
                            downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            posted BOOLEAN DEFAULT FALSE,
                            post_date TIMESTAMP NULL,
                            failed_attempts INTEGER DEFAULT 0
                        );
                        
                        CREATE TABLE IF NOT EXISTS fetch_history (
                            id SERIAL PRIMARY KEY,
                            fetch_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            images_fetched INTEGER,
                            videos_fetched INTEGER,
                            total_processed INTEGER,
                            errors TEXT
                        );
                        
                        CREATE INDEX IF NOT EXISTS idx_memes_posted ON memes(posted);
                        CREATE INDEX IF NOT EXISTS idx_memes_type ON memes(file_type);
                    """)
            logger.info("✅ Database initialized successfully")
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise
    
    def add_meme(self, post_id, title, url, file_type, file_size=0, subreddit='', score=0):
        """Add meme to database"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO memes (post_id, title, url, file_type, file_size, subreddit, score)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (post_id) DO NOTHING
                        RETURNING id;
                    """, (post_id, title[:500], url, file_type, file_size, subreddit, score))
                    
                    result = cur.fetchone()
                    if result:
                        logger.info(f"✅ Added meme: {post_id} - {title[:30]}...")
                        return True
                    return False  # Already exists
        except Exception as e:
            logger.error(f"❌ Failed to add meme: {e}")
            return False
    
    def get_next_meme(self, file_type=None):
        """Get next unposted meme"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    query = """
                        SELECT * FROM memes 
                        WHERE posted = FALSE AND failed_attempts < 3
                    """
                    params = []
                    
                    if file_type:
                        query += " AND file_type = %s"
                        params.append(file_type)
                    
                    query += " ORDER BY score DESC, downloaded_at ASC LIMIT 1"
                    
                    cur.execute(query, params)
                    return cur.fetchone()
        except Exception as e:
            logger.error(f"❌ Failed to get next meme: {e}")
            return None
    
    def mark_as_posted(self, post_id):
        """Mark meme as posted"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE memes 
                        SET posted = TRUE, post_date = CURRENT_TIMESTAMP
                        WHERE post_id = %s
                    """, (post_id,))
            logger.info(f"✅ Marked as posted: {post_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to mark as posted: {e}")
            return False
    
    def mark_as_failed(self, post_id):
        """Mark meme as failed (increment failure count)"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE memes 
                        SET failed_attempts = failed_attempts + 1
                        WHERE post_id = %s
                    """, (post_id,))
            logger.info(f"⚠️ Marked as failed: {post_id}")
        except Exception as e:
            logger.error(f"❌ Failed to update failure count: {e}")
    
    def get_stats(self):
        """Get current statistics"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total_memes,
                            SUM(CASE WHEN file_type = 'image' THEN 1 ELSE 0 END) as total_images,
                            SUM(CASE WHEN file_type = 'video' THEN 1 ELSE 0 END) as total_videos,
                            SUM(CASE WHEN posted = FALSE AND failed_attempts < 3 THEN 1 ELSE 0 END) as available,
                            SUM(CASE WHEN posted = TRUE THEN 1 ELSE 0 END) as posted,
                            MAX(downloaded_at) as last_fetch
                        FROM memes;
                    """)
                    return cur.fetchone()
        except Exception as e:
            logger.error(f"❌ Failed to get stats: {e}")
            return {}
    
    def log_fetch_session(self, images_fetched, videos_fetched, total_processed, errors=""):
        """Log fetch session results"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO fetch_history 
                        (images_fetched, videos_fetched, total_processed, errors)
                        VALUES (%s, %s, %s, %s)
                    """, (images_fetched, videos_fetched, total_processed, errors))
        except Exception as e:
            logger.error(f"❌ Failed to log fetch session: {e}")

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
        
        user = reddit.user.me()
        logger.info(f"✅ Reddit authentication successful: {user.name}")
        return reddit
        
    except Exception as e:
        logger.error(f"❌ Reddit connection failed: {e}")
        return None

def is_valid_image_url(url):
    """Check if URL points to a valid image"""
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif')
    image_domains = ['i.redd.it', 'preview.redd.it', 'i.imgur.com']
    
    return (url.endswith(image_extensions) or 
            any(domain in url for domain in image_domains))

def is_valid_video_url(url):
    """Check if URL points to a valid video"""
    return ("v.redd.it" in url or url.endswith('.mp4'))

def get_file_size(url):
    """Get file size without downloading"""
    try:
        response = requests.head(url, timeout=10)
        return int(response.headers.get('content-length', 0))
    except:
        return 0

def download_meme_temporarily(url):
    """Download meme to temporary file"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()
        
        # Create temporary file
        suffix = '.jpg'
        if url.endswith('.png'):
            suffix = '.png'
        elif url.endswith('.gif'):
            suffix = '.gif'
        elif url.endswith('.mp4'):
            suffix = '.mp4'
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                temp_file.write(chunk)
        
        temp_file.close()
        
        # Verify file
        if os.path.getsize(temp_file.name) < 1024:
            os.unlink(temp_file.name)
            return None
            
        logger.info(f"✅ Downloaded temporarily: {os.path.basename(temp_file.name)}")
        return temp_file.name
        
    except Exception as e:
        logger.error(f"❌ Download failed: {e}")
        return None

def cleanup_temp_file(filepath):
    """Clean up temporary file"""
    try:
        if filepath and os.path.exists(filepath):
            os.unlink(filepath)
            logger.info(f"🧹 Cleaned up temp file: {os.path.basename(filepath)}")
    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}")

def fetch_memes():
    """Fetch memes and store in database"""
    start_time = time.time()
    logger.info(f"🚀 Starting database meme fetch from r/{SUBREDDIT}...")
    
    # Check environment
    if not DATABASE_URL:
        logger.error("❌ DATABASE_URL not found!")
        return {"error": "Missing DATABASE_URL"}
    
    # Initialize database
    try:
        db = MemeDatabase(DATABASE_URL)
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return {"error": str(e)}
    
    # Test Reddit connection
    reddit = test_reddit_connection()
    if not reddit:
        return {"error": "Reddit connection failed"}
    
    image_count = 0
    video_count = 0
    processed = 0
    errors = []
    
    try:
        subreddit = reddit.subreddit(SUBREDDIT)
        logger.info(f"📋 Fetching from r/{SUBREDDIT}...")
        
        for submission in subreddit.hot(limit=200):
            processed += 1
            
            if submission.removed_by_category or not submission.title:
                continue
            
            logger.info(f"🔍 Processing: {submission.title[:50]}...")
            
            # Process images
            if is_valid_image_url(submission.url) and image_count < IMAGES_TO_FETCH:
                file_size = get_file_size(submission.url)
                if db.add_meme(submission.id, submission.title, submission.url, 
                              'image', file_size, SUBREDDIT, submission.score):
                    image_count += 1
                    logger.info(f"📸 Image {image_count}/{IMAGES_TO_FETCH} added")
            
            # Process videos  
            elif is_valid_video_url(submission.url) and video_count < VIDEOS_TO_FETCH:
                video_url = submission.url
                
                # Handle Reddit videos
                if hasattr(submission, 'media') and submission.media and "reddit_video" in submission.media:
                    video_url = submission.media["reddit_video"]["fallback_url"]
                
                file_size = get_file_size(video_url)
                if db.add_meme(submission.id, submission.title, video_url,
                              'video', file_size, SUBREDDIT, submission.score):
                    video_count += 1
                    logger.info(f"🎥 Video {video_count}/{VIDEOS_TO_FETCH} added")
            
            # Break if targets reached
            if image_count >= IMAGES_TO_FETCH and video_count >= VIDEOS_TO_FETCH:
                break
                
            # Respectful delay
            if processed % 10 == 0:
                time.sleep(random.uniform(1, 2))
    
    except Exception as e:
        error_msg = f"Fetch error: {str(e)}"
        errors.append(error_msg)
        logger.error(f"❌ {error_msg}")
    
    # Log session
    db.log_fetch_session(image_count, video_count, processed, "; ".join(errors))
    
    # Final stats
    elapsed_time = time.time() - start_time
    stats = db.get_stats()
    
    logger.info(f"\n🎯 Fetch Complete!")
    logger.info(f"📸 Images added: {image_count}")
    logger.info(f"🎥 Videos added: {video_count}")
    logger.info(f"📊 Total available: {stats.get('available', 0)}")
    logger.info(f"⏱️ Time: {elapsed_time:.2f}s")
    
    return {
        "images_fetched": image_count,
        "videos_fetched": video_count,
        "total_processed": processed,
        "time_elapsed": elapsed_time,
        "stats": dict(stats) if stats else {}
    }

def get_meme_for_posting(prefer_images=True):
    """Get next meme for posting to Instagram"""
    if not DATABASE_URL:
        logger.error("❌ DATABASE_URL not found!")
        return None, None
    
    db = MemeDatabase(DATABASE_URL)
    
    # Try to get preferred type first
    file_type = 'image' if prefer_images else 'video'
    meme = db.get_next_meme(file_type)
    
    # If none available, try the other type
    if not meme:
        file_type = 'video' if prefer_images else 'image'
        meme = db.get_next_meme(file_type)
    
    if not meme:
        logger.info("📭 No memes available for posting")
        return None, None
    
    logger.info(f"📋 Selected meme: {meme['title'][:50]}...")
    
    # Download temporarily
    temp_file = download_meme_temporarily(meme['url'])
    
    if temp_file:
        return meme, temp_file
    else:
        # Mark as failed and try next
        db.mark_as_failed(meme['post_id'])
        return None, None

def mark_meme_as_posted(post_id):
    """Mark meme as successfully posted"""
    if not DATABASE_URL:
        return False
    
    db = MemeDatabase(DATABASE_URL)
    return db.mark_as_posted(post_id)

def get_meme_stats():
    """Get current meme statistics"""
    if not DATABASE_URL:
        return {}
    
    try:
        db = MemeDatabase(DATABASE_URL)
        return dict(db.get_stats())
    except:
        return {}

# Test function
if __name__ == "__main__":
    print("🧪 Testing database connection...")
    result = fetch_memes()
    print(f"Result: {result}")
    
    print("\n📊 Current stats:")
    stats = get_meme_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
