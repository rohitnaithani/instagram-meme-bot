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
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
import logging
from datetime import datetime
import requests
import tempfile
import subprocess

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ====== CONFIG FROM ENVIRONMENT VARIABLES ======
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD")
DATABASE_URL = os.getenv("DATABASE_URL")

STATE_FILE = "upload_state.json"
HASHTAGS = "#memes #funny #relatable #comedy #viral #trending #lol #dankmemes #funnymemes #memesdaily #humor #laughs #mood #same #facts #reddit"

def ensure_database_schema():
    """Ensure database has required columns"""
    if not DATABASE_URL:
        return False
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Add missing columns if they don't exist
        cursor.execute("""
            ALTER TABLE memes 
            ADD COLUMN IF NOT EXISTS uploaded_to_instagram BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS uploaded_at TIMESTAMP DEFAULT NULL,
            ADD COLUMN IF NOT EXISTS instagram_post_id VARCHAR(50) DEFAULT NULL;
        """)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_memes_uploaded_instagram ON memes(uploaded_to_instagram);
            CREATE INDEX IF NOT EXISTS idx_memes_score ON memes(score DESC);
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info("✅ Database schema verified/updated")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database schema update failed: {e}")
        return False

def get_database_connection():
    """Get database connection"""
    try:
        if DATABASE_URL:
            logger.info("🔌 Connecting to PostgreSQL...")
            conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
            logger.info("✅ Database connection successful")
            return conn
        else:
            logger.error("❌ No DATABASE_URL found!")
            return None
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return None

def get_memes_from_database(posted_ids=None):
    """Fetch unposted memes from database"""
    logger.info("📋 Fetching memes from database...")
    
    if posted_ids is None:
        posted_ids = []
    
    conn = get_database_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        
        # Get unposted memes - handle both old and new schema
        if posted_ids:
            placeholders = ','.join(['%s'] * len(posted_ids))
            query = f"""
            SELECT id, post_id as reddit_id, title, url, file_type, score
            FROM memes 
            WHERE id NOT IN ({placeholders})
            AND url IS NOT NULL 
            AND (
                (uploaded_to_instagram IS NULL) OR 
                (uploaded_to_instagram = FALSE)
            )
            ORDER BY score DESC, id DESC
            LIMIT 10
            """
            cursor.execute(query, posted_ids)
        else:
            query = """
            SELECT id, post_id as reddit_id, title, url, file_type, score
            FROM memes 
            WHERE url IS NOT NULL 
            AND (
                (uploaded_to_instagram IS NULL) OR 
                (uploaded_to_instagram = FALSE)
            )
            ORDER BY score DESC, id DESC
            LIMIT 10
            """
            cursor.execute(query)
        
        memes = cursor.fetchall()
        logger.info(f"📊 Found {len(memes)} unposted memes")
        
        return [dict(meme) for meme in memes]
        
    except Exception as e:
        logger.error(f"❌ Error fetching memes: {e}")
        # Fallback query for databases without new columns
        try:
            cursor.execute("""
                SELECT id, post_id as reddit_id, title, url, file_type, 
                       COALESCE(score, 0) as score
                FROM memes 
                WHERE url IS NOT NULL 
                ORDER BY COALESCE(score, 0) DESC, id DESC
                LIMIT 10
            """)
            memes = cursor.fetchall()
            logger.info(f"📊 Fallback: Found {len(memes)} memes")
            return [dict(meme) for meme in memes]
        except Exception as e2:
            logger.error(f"❌ Fallback query also failed: {e2}")
            return []
    finally:
        if conn:
            conn.close()

def download_meme_file(url, meme_id):
    """Download meme file from URL"""
    try:
        logger.info(f"📥 Downloading meme {meme_id}...")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()
        
        # Determine file extension
        content_type = response.headers.get('content-type', '').lower()
        if 'image/jpeg' in content_type or url.lower().endswith(('.jpg', '.jpeg')):
            ext = '.jpg'
        elif 'image/png' in content_type or url.lower().endswith('.png'):
            ext = '.png'
        elif 'image/gif' in content_type or url.lower().endswith('.gif'):
            ext = '.gif'
        elif 'video/mp4' in content_type or url.lower().endswith('.mp4'):
            ext = '.mp4'
        else:
            ext = '.jpg'
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext, prefix=f"meme_{meme_id}_")
        
        # Download file
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                temp_file.write(chunk)
        
        temp_file.close()
        
        # Check file size
        file_size = os.path.getsize(temp_file.name)
        if file_size < 1024:
            os.unlink(temp_file.name)
            logger.error(f"❌ File too small: {file_size} bytes")
            return None
        
        logger.info(f"✅ Downloaded: {os.path.basename(temp_file.name)} ({file_size:,} bytes)")
        return temp_file.name
        
    except Exception as e:
        logger.error(f"❌ Download error: {e}")
        return None

def format_caption(meme_data):
    """Format Instagram caption"""
    title = meme_data.get('title', 'Funny meme')
    title = title.replace('[OC]', '').replace('[META]', '').strip()
    
    if len(title) > 120:
        title = title[:117] + "..."
    
    caption = f"{title}\n\n🔥 Fresh from Reddit 🔥\n\n{HASHTAGS}"
    return caption

def human_delay(min_seconds=2, max_seconds=5):
    """Human-like delay"""
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)

def setup_driver():
    """Setup Chrome driver with flexible ChromeDriver location"""
    logger.info("🔧 Setting up Chrome driver...")
    
    # Check Chrome
    try:
        result = subprocess.run(['google-chrome', '--version'], capture_output=True, text=True)
        logger.info(f"✅ Chrome: {result.stdout.strip()}")
    except FileNotFoundError:
        logger.error("❌ Google Chrome not found!")
        return None
    
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Try different ChromeDriver locations
    chromedriver_paths = [
        '/usr/local/bin/chromedriver',
        '/usr/bin/chromedriver',
        'chromedriver'
    ]
    
    for path in chromedriver_paths:
        try:
            logger.info(f"🚀 Trying ChromeDriver: {path}")
            if path == 'chromedriver':
                driver = webdriver.Chrome(options=chrome_options)
            else:
                service = Service(path)
                driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Test the driver
            driver.get("data:text/html,<html><body><h1>Test</h1></body></html>")
            if "Test" in driver.page_source:
                logger.info(f"✅ ChromeDriver working: {path}")
                driver.set_page_load_timeout(60)
                driver.implicitly_wait(10)
                return driver
            else:
                driver.quit()
                
        except Exception as e:
            logger.info(f"❌ Failed with {path}: {e}")
            continue
    
    logger.error("❌ No working ChromeDriver found!")
    return None


def instagram_login(driver, username, password):
    """Stealth Instagram login that bypasses bot detection"""
    logger.info(f"🥷 Stealth login for: {username}")

    try:
        # Navigate to login
        driver.get("https://www.instagram.com/accounts/login/")
        time.sleep(random.uniform(10, 18))

        # Handle cookies
        try:
            cookie_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept')]"))
            )
            ActionChains(driver).move_to_element(cookie_btn).pause(0.5).click().perform()
            time.sleep(random.uniform(2, 4))
        except:
            pass

        # Wait for form
        username_field = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='username']"))
        )

        # Human-like interaction
        ActionChains(driver).move_to_element(username_field).pause(0.5).click().perform()
        time.sleep(random.uniform(1, 2))

        username_field.clear()
        time.sleep(random.uniform(1, 2))

        # Human-like typing
        for char in username:
            username_field.send_keys(char)
            time.sleep(random.uniform(0.15, 0.45))

        # Tab to password
        time.sleep(random.uniform(2, 4))
        username_field.send_keys(Keys.TAB)
        time.sleep(random.uniform(1, 2))

        password_field = driver.find_element(By.CSS_SELECTOR, "input[name='password']")
        password_field.clear()
        time.sleep(random.uniform(1, 2))

        # Type password
        for char in password:
            password_field.send_keys(char)
            time.sleep(random.uniform(0.15, 0.4))

        # Human thinking pause
        time.sleep(random.uniform(5, 10))

        # Submit
        password_field.send_keys(Keys.RETURN)
        time.sleep(random.uniform(15, 25))

        # Check success
        if "/accounts/login" not in driver.current_url:
            try:
                WebDriverWait(driver, 10).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/explore/')]")),
                        EC.presence_of_element_located((By.XPATH, "//span[text()='Create']"))
                    )
                )
                logger.info("🎉 Stealth login successful!")

                # Handle popups
                for _ in range(3):
                    try:
                        popup = WebDriverWait(driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Not Now')]"))
                        )
                        ActionChains(driver).move_to_element(popup).pause(0.5).click().perform()
                        time.sleep(random.uniform(2, 4))
                    except:
                        break

                return True
            except:
                logger.error("❌ Redirected but no logged-in elements")
                return False
        else:
            logger.error("❌ Login failed - still on login page")
            return False

    except Exception as e:
        logger.error(f"❌ Stealth login error: {e}")
        return False

# Also update your setup_driver function:
def setup_driver():
    """Enhanced driver setup for production"""
    logger.info("🔧 Setting up production driver...")

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1366,768")

    # Add all stealth options from create_stealth_driver function above
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--disable-default-apps")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    try:
        service = Service('/usr/local/bin/chromedriver')
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # Execute the same stealth script from above
        driver.execute_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            window.chrome = {runtime: {}};
            delete navigator.__proto__.webdriver;
        """)

        return driver
    except Exception as e:
        logger.error(f"❌ Production driver setup failed: {e}")
        return None
        
def upload_post(driver, file_path, caption):
    """Simplified Instagram upload"""
    logger.info(f"📤 Uploading: {os.path.basename(file_path)}")
    
    try:
        # Go home and find create button
        driver.get("https://www.instagram.com/")
        human_delay(3, 5)
        
        create_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[text()='Create']"))
        )
        driver.execute_script("arguments[0].click();", create_btn)
        human_delay(3, 5)
        
        # Upload file
        file_input = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
        )
        file_input.send_keys(os.path.abspath(file_path))
        human_delay(5, 8)
        
        # Click Next buttons
        for i in range(3):
            try:
                next_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Next')]"))
                )
                driver.execute_script("arguments[0].click();", next_btn)
                human_delay(3, 5)
            except:
                break
        
        # Add caption
        try:
            caption_area = WebDriverWait(driver, 8).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "textarea[aria-label*='caption']"))
            )
            caption_area.clear()
            caption_area.send_keys(caption)
            human_delay(2, 4)
        except:
            logger.warning("⚠️ Could not add caption")
        
        # Share
        share_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Share')]"))
        )
        driver.execute_script("arguments[0].click();", share_btn)
        
        human_delay(15, 20)
        logger.info("✅ Upload completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Upload failed: {e}")
        return False

def mark_meme_as_posted(meme_id):
    """Mark meme as posted in database"""
    logger.info(f"📝 Marking meme {meme_id} as posted...")
    
    conn = get_database_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Try new schema first
        try:
            cursor.execute("""
                UPDATE memes 
                SET uploaded_to_instagram = TRUE, uploaded_at = %s 
                WHERE id = %s
            """, (datetime.now(), meme_id))
        except Exception:
            # Fallback for old schema - add note to title or use a flag table
            logger.info("Using fallback marking method")
            cursor.execute("""
                UPDATE memes 
                SET title = title || ' [POSTED]'
                WHERE id = %s AND title NOT LIKE '%[POSTED]%'
            """, (meme_id,))
        
        conn.commit()
        logger.info(f"✅ Marked meme {meme_id} as posted")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error marking as posted: {e}")
        return False
    finally:
        if conn:
            conn.close()

def load_state():
    """Load upload state"""
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

def main():
    """Main function"""
    logger.info("🚀 Starting Instagram uploader...")
    logger.info("=" * 60)
    
    # Check credentials
    if not all([INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD]):
        logger.error("❌ Missing Instagram credentials!")
        return False
    
    if not DATABASE_URL:
        logger.error("❌ Missing DATABASE_URL!")
        return False
    
    logger.info(f"✅ Credentials loaded for: {INSTAGRAM_USERNAME}")
    
    # Ensure database schema
    if not ensure_database_schema():
        logger.warning("⚠️ Database schema update failed, trying anyway...")
    
    # Test database
    test_conn = get_database_connection()
    if not test_conn:
        logger.error("❌ Database connection failed!")
        return False
    test_conn.close()
    
    # Load state
    state = load_state()
    posted_ids = state.get("posted_meme_ids", [])
    logger.info(f"📊 Previously posted: {len(posted_ids)} memes")
    
    # Get memes
    memes = get_memes_from_database(posted_ids)
    if not memes:
        logger.error("❌ No memes available!")
        return False
    
    meme = memes[0]
    logger.info(f"🎯 Selected: {meme['title'][:50]}... (Score: {meme.get('score', 0)})")
    
    # Download meme
    temp_file = download_meme_file(meme['url'], meme['id'])
    if not temp_file:
        logger.error("❌ Download failed")
        return False
    
    # Setup driver
    driver = setup_driver()
    if not driver:
        logger.error("❌ Chrome setup failed")
        return False
    
    success = False
    try:
        # Login
        if not instagram_login(driver, INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD):
            logger.error("❌ Login failed")
            return False
        
        # Upload
        caption = format_caption(meme)
        if upload_post(driver, temp_file, caption):
            # Mark as posted
            mark_meme_as_posted(meme['id'])
            posted_ids.append(meme['id'])
            state["posted_meme_ids"] = posted_ids
            state["last_upload_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_state(state)
            
            logger.info("🎉 SUCCESS!")
            logger.info(f"   Meme: {meme['title']}")
            success = True
        else:
            logger.error("❌ Upload failed")
    
    except Exception as e:
        logger.error(f"❌ Error: {e}")
    
    finally:
        # Cleanup
        if temp_file and os.path.exists(temp_file):
            os.unlink(temp_file)
            logger.info("🧹 Temp file cleaned")
        
        if driver:
            driver.quit()
            logger.info("🔒 Driver closed")
    
    logger.info("=" * 60)
    return success

if __name__ == "__main__":
    success = main()
    if success:
        print("✅ Instagram upload completed!")
    else:
        print("❌ Instagram upload failed")
        exit(1)
