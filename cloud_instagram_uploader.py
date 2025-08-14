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
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
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
            logger.info(f"  - {meme_dict['title'][:50]}... (ID: {meme_dict['id']})")
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

def format_caption(meme_data):
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
    """Setup Chrome driver with fixed version compatibility for Render"""
    logger.info("🔧 Setting up Chrome driver for cloud deployment...")
    
    chrome_options = Options()
    
    # Essential cloud options for Render
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--start-maximized")
    
    # Memory and performance optimization
    chrome_options.add_argument("--memory-pressure-off")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--disable-client-side-phishing-detection")
    chrome_options.add_argument("--disable-crash-reporter")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-features=TranslateUI")
    chrome_options.add_argument("--disable-ipc-flooding-protection")
    
    # Anti-detection measures
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Set a realistic user agent
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Disable notifications and location
    prefs = {
        "profile.default_content_setting_values": {
            "notifications": 2,
            "geolocation": 2,
        },
        "profile.default_content_settings.popups": 0,
        "profile.managed_default_content_settings.images": 2
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    try:
        # Use webdriver-manager to automatically handle ChromeDriver versions
        logger.info("🚀 Setting up ChromeDriver with webdriver-manager...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Execute anti-detection scripts
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
        driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
        
        driver.set_page_load_timeout(60)
        logger.info("✅ Chrome driver initialized successfully with webdriver-manager")
        return driver
        
    except Exception as e:
        logger.error(f"❌ Failed to start Chrome driver with webdriver-manager: {e}")
        
        # Fallback: Try without webdriver-manager
        try:
            logger.info("🔄 Trying fallback Chrome setup without webdriver-manager...")
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(60)
            logger.info("✅ Chrome driver initialized with fallback method")
            return driver
        except Exception as e2:
            logger.error(f"❌ Fallback Chrome setup also failed: {e2}")
            logger.error("💡 Make sure Chrome is installed on the system")
            
        return None

def instagram_login(driver, username, password):
    """Enhanced Instagram login with better error handling"""
    logger.info("🔑 Starting Instagram login...")
    
    try:
        # Go to login page
        logger.info("📱 Navigating to Instagram login page...")
        driver.get("https://www.instagram.com/accounts/login/")
        human_delay(5, 8)
        
        # Handle cookie banners
        try:
            accept_selectors = [
                "//button[contains(text(), 'Accept')]",
                "//button[contains(text(), 'Allow')]",
                "//button[contains(text(), 'Accept All')]"
            ]
            
            for selector in accept_selectors:
                try:
                    accept_btn = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    accept_btn.click()
                    logger.info("✅ Cookie banner accepted")
                    human_delay(1, 2)
                    break
                except:
                    continue
        except:
            logger.info("ℹ️  No cookie banner found")
        
        # Wait for login form
        logger.info("⏳ Waiting for login form...")
        username_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        
        # Type username slowly
        logger.info(f"👤 Entering username: {username}")
        username_field.clear()
        for char in username:
            username_field.send_keys(char)
            time.sleep(random.uniform(0.1, 0.3))
        
        logger.info("✅ Username entered")
        human_delay(2, 3)
        
        # Type password
        password_field = driver.find_element(By.NAME, "password")
        password_field.clear()
        logger.info("🔒 Entering password...")
        for i, char in enumerate(password):
            password_field.send_keys(char)
            time.sleep(random.uniform(0.1, 0.3))
            # Don't log the actual password
            if i == 0:
                logger.info("🔒 Password entry started...")
        
        logger.info("✅ Password entered")
        human_delay(3, 5)
        
        # Submit login
        logger.info("🚀 Submitting login...")
        try:
            login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
        except:
            password_field.send_keys(Keys.RETURN)
        
        logger.info("🔄 Login submitted, waiting for response...")
        human_delay(8, 12)
        
        # Check for success indicators
        try:
            success_indicators = [
                "//a[@href='/direct/inbox/']",
                "//svg[@aria-label='Home']", 
                "//*[@aria-label='New post']",
                "//a[contains(@href, '/direct/')]",
                "//span[text()='Create']"
            ]
            
            WebDriverWait(driver, 15).until(
                EC.any_of(*[EC.presence_of_element_located((By.XPATH, indicator)) for indicator in success_indicators])
            )
            logger.info("✅ Login successful - Instagram home page loaded")
            
            # Handle post-login popups
            logger.info("🔄 Handling post-login popups...")
            popup_selectors = [
                "//button[contains(text(), 'Not now')]",
                "//button[contains(text(), 'Not Now')]", 
                "//button[text()='Not Now']",
                "//button[contains(text(), 'Skip')]",
                "//button[contains(text(), 'Maybe Later')]"
            ]
            
            for popup_xpath in popup_selectors:
                try:
                    popup = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, popup_xpath))
                    )
                    popup.click()
                    logger.info("✅ Popup dismissed")
                    human_delay(2, 3)
                except:
                    continue
            
            return True
            
        except:
            logger.error("❌ Login failed - no success indicators found")
            
            # Check for specific error messages
            try:
                error_messages = driver.find_elements(By.XPATH, "//*[contains(text(), 'incorrect') or contains(text(), 'error') or contains(text(), 'wrong')]")
                if error_messages:
                    logger.error(f"❌ Login error detected: {error_messages[0].text}")
            except:
                pass
            
            return False
            
    except Exception as e:
        logger.error(f"❌ Login error: {e}")
        return False

def upload_post(driver, file_path, caption):
    """Upload a post to Instagram with enhanced error handling"""
    logger.info(f"📤 Starting upload: {os.path.basename(file_path)}")
    
    try:
        # Go to Instagram home
        logger.info("🏠 Navigating to Instagram home...")
        driver.get("https://www.instagram.com/")
        human_delay(3, 5)
        
        # Click create post button
        logger.info("➕ Looking for Create button...")
        create_selectors = [
            "//svg[@aria-label='New post']",
            "//*[@aria-label='New post']", 
            "//span[text()='Create']",
            "//div[@role='menuitem']//span[contains(text(), 'Create')]",
            "//*[contains(@aria-label, 'Create')]"
        ]
        
        create_clicked = False
        for i, selector in enumerate(create_selectors):
            try:
                logger.info(f"🔍 Trying create selector {i+1}/{len(create_selectors)}")
                create_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                create_btn.click()
                create_clicked = True
                logger.info("✅ Create button clicked successfully")
                break
            except Exception as e:
                logger.info(f"❌ Create selector {i+1} failed: {str(e)[:100]}...")
                continue
        
        if not create_clicked:
            logger.error("❌ Could not find create post button")
            return False
        
        human_delay(2, 4)
        
        # Upload file
        logger.info(f"📁 Uploading file: {file_path}")
        try:
            file_input = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='file']"))
            )
            file_input.send_keys(os.path.abspath(file_path))
            logger.info("✅ File selected successfully")
        except Exception as e:
            logger.error(f"❌ Could not find file input: {e}")
            return False
        
        human_delay(5, 8)
        
        # Click Next button(s) - Instagram usually has 2-3 Next buttons
        logger.info("⏭️ Proceeding through upload steps...")
        for step in range(3):
            try:
                next_btn = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Next')]"))
                )
                next_btn.click()
                logger.info(f"✅ Next button {step + 1} clicked")
                human_delay(3, 5)
            except Exception as e:
                logger.info(f"ℹ️  No more Next buttons at step {step + 1}: {str(e)[:50]}...")
                break
        
        # Add caption
        logger.info("📝 Adding caption...")
        try:
            caption_selectors = [
                "//textarea[@aria-label='Write a caption...']",
                "//div[@contenteditable='true'][@aria-label='Write a caption...']",
                "//textarea[contains(@placeholder, 'caption')]"
            ]
            
            caption_added = False
            for selector in caption_selectors:
                try:
                    caption_area = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    
                    # Type caption slowly to avoid detection
                    caption_area.clear()
                    logger.info(f"📝 Typing caption: {caption[:50]}...")
                    for char in caption:
                        caption_area.send_keys(char)
                        time.sleep(random.uniform(0.05, 0.15))
                    
                    caption_added = True
                    logger.info("✅ Caption added successfully")
                    break
                except:
                    continue
            
            if not caption_added:
                logger.warning("⚠️  Could not add caption - continuing anyway")
        except Exception as e:
            logger.warning(f"⚠️  Caption error: {e}")
        
        human_delay(2, 4)
        
        # Share post
        logger.info("🚀 Sharing post...")
        try:
            share_selectors = [
                "//button[contains(text(), 'Share')]",
                "//button[contains(@aria-label, 'Share')]",
                "//*[text()='Share']"
            ]
            
            shared = False
            for selector in share_selectors:
                try:
                    share_btn = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    share_btn.click()
                    shared = True
                    logger.info("✅ Share button clicked")
                    break
                except:
                    continue
            
            if not shared:
                logger.error("❌ Could not find Share button")
                return False
        except Exception as e:
            logger.error(f"❌ Share button error: {e}")
            return False
        
        # Wait for upload completion
        logger.info("⏳ Waiting for upload completion...")
        human_delay(10, 15)
        
        # Check for success indicators
        try:
            success_selectors = [
                "//*[contains(text(), 'Your post has been shared')]",
                "//*[contains(text(), 'Post shared')]",
                "//svg[@aria-label='Home']",
                "//*[@aria-label='Activity Feed']"
            ]
            
            WebDriverWait(driver, 20).until(
                EC.any_of(*[EC.presence_of_element_located((By.XPATH, selector)) for selector in success_selectors])
            )
            logger.info("🎉 Upload completed successfully!")
            return True
            
        except:
            logger.info("⚠️  Upload timeout - assuming success (Instagram sometimes doesn't show confirmation)")
            return True  # Assume success if no clear failure
            
    except Exception as e:
        logger.error(f"❌ Upload failed with error: {e}")
        return False

def mark_meme_as_posted(meme_id):
    """Mark meme as posted in database"""
    logger.info(f"📝 Marking meme {meme_id} as posted in database...")
    
    conn = get_database_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Check if uploaded_to_instagram column exists, if not create it
        try:
            cursor.execute("""
                ALTER TABLE memes 
                ADD COLUMN IF NOT EXISTS uploaded_to_instagram BOOLEAN DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS uploaded_at TIMESTAMP NULL
            """)
            conn.commit()
        except:
            pass  # Column might already exist
        
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
    logger.info("=" * 60)
    
    # Check credentials
    if not all([INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD]):
        logger.error("❌ Missing Instagram credentials!")
        logger.error("💡 Set INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD in Render environment")
        return False
    
    logger.info(f"✅ Instagram credentials loaded for user: {INSTAGRAM_USERNAME}")
    
    # Test database connection
    logger.info("🔌 Testing database connection...")
    if not get_database_connection():
        logger.error("❌ Database connection failed!")
        return False
    
    # Load state
    state = load_state()
    posted_meme_ids = state.get("posted_meme_ids", [])
    logger.info(f"📊 Previously posted memes: {len(posted_meme_ids)}")
    
    # Get memes from database
    memes = get_memes_from_database(posted_meme_ids)
    
    if not memes:
        logger.error("❌ No unposted memes found in database!")
        logger.error("💡 Make sure the meme fetcher has run and stored memes in PostgreSQL")
        return False
    
    logger.info(f"📤 Found {len(memes)} memes available to post")
    
    # Select first meme to post
    meme_to_post = memes[0]
    logger.info("🎯 Selected meme for upload:")
    logger.info(f"   ID: {meme_to_post['id']}")
    logger.info(f"   Title: {meme_to_post['title'][:80]}...")
    logger.info(f"   Reddit ID: {meme_to_post['reddit_id']}")
    logger.info(f"   URL: {meme_to_post['url']}")
    
    # Download the meme file
    logger.info("📥 Downloading meme file...")
    temp_file_path = download_meme_file(meme_to_post['url'], meme_to_post['id'])
    if not temp_file_path:
        logger.error("❌ Failed to download meme file")
        return False
    
    # Setup driver
    driver = setup_driver()
    if not driver:
        logger.error("❌ Failed to setup Chrome driver")
        return False
    
    success = False
    try:
        # Login
        if not instagram_login(driver, INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD):
            logger.error("❌ Instagram login failed")
            return False
        
        # Format caption from meme data
        caption = format_caption(meme_to_post)
        logger.info(f"📝 Generated caption: {caption[:100]}...")
        
        # Upload post
        if upload_post(driver, temp_file_path, caption):
            # Mark as posted in database and local state
            mark_meme_as_posted(meme_to_post['id'])
            
            posted_meme_ids.append(meme_to_post['id'])
            state["posted_meme_ids"] = posted_meme_ids
            state["last_upload_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_state(state)
            
            logger.info("🎉 SUCCESS! Meme uploaded to Instagram")
            logger.info(f"   Meme ID: {meme_to_post['id']}")
            logger.info(f"   Title: {meme_to_post['title']}")
            logger.info(f"   Upload time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            success = True
        else:
            logger.error("❌ Upload failed")
    
    except Exception as e:
        logger.error(f"❌ Unexpected error during upload: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
    
    finally:
        # Clean up temporary file
        if 'temp_file_path' in locals() and temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                logger.info("🧹 Temporary file cleaned up")
            except Exception as e:
                logger.warning(f"⚠️  Could not clean up temp file: {e}")
        
        # Close driver
        try:
            if driver:
                driver.quit()
                logger.info("🔒 Chrome driver closed")
        except Exception as e:
            logger.warning(f"⚠️  Error closing driver: {e}")
    
    logger.info("=" * 60)
    return success

if __name__ == "__main__":
    success = main()
    if success:
        print("✅ Instagram upload completed successfully!")
    else:
        print("❌ Instagram upload failed - check logs for details")
        exit(1)
