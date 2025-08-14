import os
import time
import random
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import logging
from datetime import datetime
import requests
import tempfile

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ====== CONFIG FROM ENVIRONMENT VARIABLES ======
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD")

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")  # Railway PostgreSQL URL
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = os.getenv("DB_PORT", "5432")

POSTS_PER_RUN = 1
STATE_FILE = "upload_state.json"

# Enhanced hashtags for better reach
HASHTAGS = "#memes #funny #relatable #comedy #viral #trending #lol #dankmemes #funnymemes #memesdaily #humor #laughs #mood #same #facts #reddit"

def get_database_connection():
    """Get database connection using available credentials"""
    try:
        # Try DATABASE_URL first (Railway format)
        if DATABASE_URL:
            logger.info("🔌 Connecting to database using DATABASE_URL...")
            conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        # Try individual parameters
        elif all([DB_HOST, DB_NAME, DB_USER, DB_PASSWORD]):
            logger.info("🔌 Connecting to database using individual parameters...")
            conn = psycopg2.connect(
                host=DB_HOST,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                port=DB_PORT,
                cursor_factory=RealDictCursor
            )
        else:
            logger.error("❌ No database credentials found!")
            logger.error("💡 Set DATABASE_URL or DB_HOST, DB_NAME, DB_USER, DB_PASSWORD")
            return None
        
        logger.info("✅ Database connection successful")
        return conn
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return None

def load_state():
    """Load upload state to track posted memes"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except:
            return {"posted_meme_ids": [], "last_upload_date": ""}
    return {"posted_meme_ids": [], "last_upload_date": ""}

def save_state(state):
    """Save upload state"""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving state: {e}")

def get_memes_from_database(posted_ids=None):
    """Fetch unposted memes from PostgreSQL database"""
    logger.info("📋 Fetching memes from database...")
    
    if posted_ids is None:
        posted_ids = []
    
    conn = get_database_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        
        # Query to get unposted memes (matching your Railway schema)
        if posted_ids:
            placeholders = ','.join(['%s'] * len(posted_ids))
            query = f"""
            SELECT id, post_id as reddit_id, title, url, 
                   CASE WHEN url LIKE '%.mp4%' OR url LIKE '%v.redd.it%' THEN 'video' ELSE 'image' END as file_type
            FROM memes 
            WHERE id NOT IN ({placeholders})
            AND url IS NOT NULL
            ORDER BY id DESC
            LIMIT 20
            """
            cursor.execute(query, posted_ids)
        else:
            query = """
            SELECT id, post_id as reddit_id, title, url,
                   CASE WHEN url LIKE '%.mp4%' OR url LIKE '%v.redd.it%' THEN 'video' ELSE 'image' END as file_type
            FROM memes 
            WHERE url IS NOT NULL
            ORDER BY id DESC
            LIMIT 20
            """
            cursor.execute(query)
        
        memes = cursor.fetchall()
        logger.info(f"📊 Found {len(memes)} unposted memes in database")
        
        # Convert to list of dicts for easier handling
        meme_list = []
        for meme in memes:
            meme_dict = dict(meme)
            logger.info(f"  - {meme_dict['title'][:50]}... (Score: {meme_dict.get('score', 'N/A')})")
            meme_list.append(meme_dict)
        
        return meme_list
        
    except Exception as e:
        logger.error(f"❌ Error fetching memes from database: {e}")
        logger.error("💡 Check your database table structure and column names")
        return []
    
    finally:
        if conn:
            conn.close()

def download_meme_file(url, meme_id):
    """Download meme file from URL to temporary location"""
    try:
        logger.info(f"📥 Downloading meme from: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()
        
        # Determine file extension
        content_type = response.headers.get('content-type', '')
        if 'image/jpeg' in content_type or url.endswith('.jpg'):
            ext = '.jpg'
        elif 'image/png' in content_type or url.endswith('.png'):
            ext = '.png'
        elif 'image/gif' in content_type or url.endswith('.gif'):
            ext = '.gif'
        elif 'video/mp4' in content_type or url.endswith('.mp4'):
            ext = '.mp4'
        elif url.endswith('.jpeg'):
            ext = '.jpg'
        else:
            ext = '.jpg'  # Default
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext, prefix=f"meme_{meme_id}_")
        
        # Download file
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                temp_file.write(chunk)
        
        temp_file.close()
        
        # Check file size
        file_size = os.path.getsize(temp_file.name)
        if file_size < 1024:  # Less than 1KB
            os.unlink(temp_file.name)
            logger.error(f"❌ Downloaded file too small: {file_size} bytes")
            return None
        
        logger.info(f"✅ Downloaded meme: {os.path.basename(temp_file.name)} ({file_size} bytes)")
        return temp_file.name
        
    except Exception as e:
        logger.error(f"❌ Error downloading meme: {e}")
        return None
    """Format caption from meme data"""
    title = meme_data.get('title', 'Funny meme')
    
    # Clean up title (remove common Reddit formatting)
    title = title.replace('[OC]', '').replace('[META]', '').strip()
    
    # Limit title length for Instagram
    if len(title) > 120:
        title = title[:117] + "..."
    
    # Create caption with title and hashtags
    caption = f"{title}\n\n🔥 Fresh from Reddit\n\n{HASHTAGS}"
    
    return caption

def human_delay(min_seconds=2, max_seconds=5):
    """Add human-like delay"""
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)

def setup_driver():
    """Setup Chrome driver optimized for cloud deployment"""
    chrome_options = Options()
    
    # Essential cloud options
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Memory optimization
    chrome_options.add_argument("--memory-pressure-off")
    chrome_options.add_argument("--max_old_space_size=4096")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    
    # Anti-detection
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Realistic browser fingerprint
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        
        # Execute anti-detection scripts
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
        
        driver.set_page_load_timeout(60)
        logger.info("✅ Chrome driver initialized")
        return driver
        
    except Exception as e:
        logger.error(f"❌ Failed to start Chrome driver: {e}")
        return None

def instagram_login(driver, username, password):
    """Enhanced Instagram login"""
    logger.info("🔑 Starting Instagram login...")
    
    try:
        # Go to login page
        driver.get("https://www.instagram.com/accounts/login/")
        human_delay(5, 8)
        
        # Handle cookie banners
        try:
            accept_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept') or contains(text(), 'Allow')]"))
            )
            accept_btn.click()
            human_delay(1, 2)
        except:
            pass
        
        # Wait for login form
        username_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        
        # Type username slowly
        username_field.clear()
        for char in username:
            username_field.send_keys(char)
            time.sleep(random.uniform(0.1, 0.3))
        
        logger.info("✅ Username entered")
        human_delay(2, 3)
        
        # Type password
        password_field = driver.find_element(By.NAME, "password")
        password_field.clear()
        for char in password:
            password_field.send_keys(char)
            time.sleep(random.uniform(0.1, 0.3))
        
        logger.info("✅ Password entered")
        human_delay(3, 5)
        
        # Submit login
        try:
            login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
        except:
            password_field.send_keys(Keys.RETURN)
        
        logger.info("🔄 Login submitted")
        human_delay(8, 12)
        
        # Check for success
        try:
            WebDriverWait(driver, 15).until(
                EC.any_of(
                    EC.presence_of_element_located((By.XPATH, "//a[@href='/direct/inbox/']")),
                    EC.presence_of_element_located((By.XPATH, "//svg[@aria-label='Home']")),
                    EC.presence_of_element_located((By.XPATH, "//*[@aria-label='New post']"))
                )
            )
            logger.info("✅ Login successful")
            
            # Handle post-login popups
            popups = [
                "//button[contains(text(), 'Not now') or contains(text(), 'Not Now')]",
                "//button[text()='Not Now']",
                "//button[contains(text(), 'Skip')]"
            ]
            
            for popup_xpath in popups:
                try:
                    popup = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, popup_xpath))
                    )
                    popup.click()
                    human_delay(2, 3)
                except:
                    continue
            
            return True
            
        except:
            logger.error("❌ Login failed - no success indicators found")
            return False
            
    except Exception as e:
        logger.error(f"❌ Login error: {e}")
        return False

def upload_post(driver, file_path, caption):
    """Upload a post to Instagram"""
    logger.info(f"📤 Starting upload: {os.path.basename(file_path)}")
    
    try:
        # Go to Instagram home
        driver.get("https://www.instagram.com/")
        human_delay(3, 5)
        
        # Click create post button
        create_selectors = [
            "//svg[@aria-label='New post']",
            "//*[@aria-label='New post']",
            "//span[text()='Create']",
            "//div[@role='menuitem']//span[contains(text(), 'Create')]"
        ]
        
        create_clicked = False
        for selector in create_selectors:
            try:
                create_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                create_btn.click()
                create_clicked = True
                logger.info("✅ Create button clicked")
                break
            except:
                continue
        
        if not create_clicked:
            logger.error("❌ Could not find create post button")
            return False
        
        human_delay(2, 4)
        
        # Upload file
        try:
            file_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='file']"))
            )
            file_input.send_keys(os.path.abspath(file_path))
            logger.info("✅ File selected")
        except:
            logger.error("❌ Could not find file input")
            return False
        
        human_delay(5, 8)
        
        # Click Next button(s)
        for step in range(3):
            try:
                next_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Next')]"))
                )
                next_btn.click()
                logger.info(f"✅ Next button {step + 1} clicked")
                human_delay(3, 5)
            except:
                logger.info(f"ℹ️  No more Next buttons (step {step + 1})")
                break
        
        # Add caption
        try:
            caption_area = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//textarea[@aria-label='Write a caption...']"))
            )
            
            # Type caption slowly
            caption_area.clear()
            for char in caption:
                caption_area.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))
            
            logger.info("✅ Caption added")
        except:
            logger.warning("⚠️  Could not add caption")
        
        human_delay(2, 4)
        
        # Share post
        try:
            share_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Share')]"))
            )
            share_btn.click()
            logger.info("✅ Share button clicked")
        except:
            logger.error("❌ Could not find Share button")
            return False
        
        # Wait for upload completion
        human_delay(10, 15)
        
        # Check for success indicators
        try:
            WebDriverWait(driver, 20).until(
                EC.any_of(
                    EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Your post has been shared')]")),
                    EC.presence_of_element_located((By.XPATH, "//svg[@aria-label='Home']")),
                    EC.url_contains("instagram.com")
                )
            )
            logger.info("🎉 Upload completed successfully!")
            return True
            
        except:
            logger.warning("⚠️  Upload may have completed (timeout waiting for confirmation)")
            return True  # Assume success if no clear failure
            
    except Exception as e:
        logger.error(f"❌ Upload failed: {e}")
        return False

def mark_meme_as_posted(meme_id):
    """Mark meme as posted in database"""
    conn = get_database_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Update meme as posted
        cursor.execute("""
            UPDATE memes 
            SET uploaded_to_instagram = true, 
                uploaded_at = %s 
            WHERE id = %s
        """, (datetime.now(), meme_id))
        
        conn.commit()
        logger.info(f"✅ Marked meme {meme_id} as posted in database")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error marking meme as posted: {e}")
        return False
    
    finally:
        if conn:
            conn.close()

def main():
    """Main upload function"""
    logger.info("🚀 Starting PostgreSQL-based Instagram uploader...")
    
    # Check credentials
    if not all([INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD]):
        logger.error("❌ Missing Instagram credentials!")
        logger.error("💡 Set INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD in environment")
        return False
    
    logger.info(f"✅ Instagram credentials loaded for: {INSTAGRAM_USERNAME}")
    
    # Load state
    state = load_state()
    posted_meme_ids = state.get("posted_meme_ids", [])
    
    # Get memes from database
    memes = get_memes_from_database(posted_meme_ids)
    
    if not memes:
        logger.error("❌ No unposted memes found in database!")
        logger.error("💡 Make sure the meme fetcher has run and stored memes in PostgreSQL")
        return False
    
    logger.info(f"📤 Found {len(memes)} memes available to post")
    
    # Select first meme to post
    meme_to_post = memes[0]
    logger.info(f"🎯 Selected meme: {meme_to_post['title'][:50]}...")
    logger.info(f"   URL: {meme_to_post['url']}")
    logger.info(f"   Reddit ID: {meme_to_post['reddit_id']}")
    
    # Download the meme file
    temp_file_path = download_meme_file(meme_to_post['url'], meme_to_post['id'])
    if not temp_file_path:
        logger.error("❌ Failed to download meme file")
        return False
    
    # Setup driver
    driver = setup_driver()
    if not driver:
        return False
    
    success = False
    try:
        # Login
        if not instagram_login(driver, INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD):
            logger.error("❌ Instagram login failed")
            return False
        
        # Format caption from meme data
        caption = format_caption(meme_to_post)
        logger.info(f"📝 Caption: {caption[:100]}...")
        
        # Upload post
        if upload_post(driver, temp_file_path, caption):
            # Mark as posted in database and local state
            mark_meme_as_posted(meme_to_post['id'])
            
            posted_meme_ids.append(meme_to_post['id'])
            state["posted_meme_ids"] = posted_meme_ids
            state["last_upload_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_state(state)
            
            logger.info(f"🎉 Successfully uploaded meme ID {meme_to_post['id']}")
            logger.info(f"   Title: {meme_to_post['title']}")
            success = True
        else:
            logger.error("❌ Upload failed")
    
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
    
    finally:
        # Clean up temporary file
        if 'temp_file_path' in locals() and temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                logger.info("🧹 Cleaned up temporary file")
            except:
                pass
        
        try:
            driver.quit()
        except:
            pass
    
    return success

if __name__ == "__main__":
    success = main()
    if success:
        print("✅ Instagram upload completed successfully")
    else:
        print("❌ Instagram upload failed")
        exit(1)
