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

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")

STATE_FILE = "upload_state.json"

# Enhanced hashtags
HASHTAGS = "#memes #funny #relatable #comedy #viral #trending #lol #dankmemes #funnymemes #memesdaily #humor #laughs #mood #same #facts #reddit"

def get_database_connection():
    """Get Railway database connection"""
    try:
        if DATABASE_URL:
            logger.info("🔌 Connecting to Railway PostgreSQL...")
            conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
            logger.info("✅ Railway database connection successful")
            return conn
        else:
            logger.error("❌ No DATABASE_URL found!")
            return None
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return None

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

def get_memes_from_database(posted_ids=None):
    """Fetch unposted memes from Railway database"""
    logger.info("📋 Fetching memes from Railway database...")
    
    if posted_ids is None:
        posted_ids = []
    
    conn = get_database_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        
        # Get unposted memes
        if posted_ids:
            placeholders = ','.join(['%s'] * len(posted_ids))
            query = f"""
            SELECT id, post_id as reddit_id, title, url, file_type
            FROM memes 
            WHERE id NOT IN ({placeholders})
            AND url IS NOT NULL 
            AND (uploaded_to_instagram IS NULL OR uploaded_to_instagram = FALSE)
            ORDER BY id DESC
            LIMIT 10
            """
            cursor.execute(query, posted_ids)
        else:
            query = """
            SELECT id, post_id as reddit_id, title, url, file_type
            FROM memes 
            WHERE url IS NOT NULL 
            AND (uploaded_to_instagram IS NULL OR uploaded_to_instagram = FALSE)
            ORDER BY id DESC
            LIMIT 10
            """
            cursor.execute(query)
        
        memes = cursor.fetchall()
        logger.info(f"📊 Found {len(memes)} unposted memes")
        
        return [dict(meme) for meme in memes]
        
    except Exception as e:
        logger.error(f"❌ Error fetching memes: {e}")
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
    
    # Check Chrome first
    try:
        result = subprocess.run(['google-chrome', '--version'], capture_output=True, text=True)
        logger.info(f"✅ Chrome found: {result.stdout.strip()}")
    except FileNotFoundError:
        logger.error("❌ Google Chrome not found!")
        return None
    
    chrome_options = Options()
    
    # Essential cloud deployment options
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
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Realistic user agent
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Disable unnecessary features to save resources
    prefs = {
        "profile.default_content_setting_values": {
            "notifications": 2,
            "geolocation": 2,
        },
        "profile.default_content_settings.popups": 0,
        "profile.managed_default_content_settings.images": 2  # Don't load images
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    # Try different ChromeDriver locations
    chromedriver_paths = [
        '/usr/local/bin/chromedriver',  # Custom installation
        '/usr/bin/chromedriver',        # System package
        'chromedriver'                  # PATH lookup
    ]
    
    driver = None
    for path in chromedriver_paths:
        try:
            logger.info(f"🚀 Trying ChromeDriver at: {path}")
            if path == 'chromedriver':
                # Let selenium find it in PATH
                driver = webdriver.Chrome(options=chrome_options)
            else:
                service = Service(path)
                driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info(f"✅ ChromeDriver working: {path}")
            break
        except Exception as e:
            logger.info(f"❌ Failed with {path}: {e}")
            continue
    
    if not driver:
        logger.error("❌ No working ChromeDriver found!")
        return None
    
    # Enhanced anti-detection scripts
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
    driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
    
    driver.set_page_load_timeout(60)
    driver.implicitly_wait(10)
    
    logger.info("✅ Chrome driver initialized successfully")
    return driver

def instagram_login(driver, username, password):
    """Instagram login with improved error handling"""
    logger.info(f"🔑 Logging into Instagram as {username}")
    
    try:
        # Navigate to login page
        driver.get("https://www.instagram.com/accounts/login/")
        human_delay(5, 8)
        
        # Wait for page to load
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        logger.info("📱 Instagram page loaded")
        
        # Handle cookie consent
        cookie_selectors = [
            "//button[contains(text(), 'Accept')]",
            "//button[contains(text(), 'Allow')]", 
            "//button[contains(text(), 'Accept All')]"
        ]
        
        for selector in cookie_selectors:
            try:
                cookie_btn = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                cookie_btn.click()
                logger.info("✅ Cookies accepted")
                human_delay(1, 2)
                break
            except:
                continue
        
        # Find username field
        username_selectors = [
            "input[name='username']",
            "input[aria-label='Phone number, username, or email']"
        ]
        
        username_field = None
        for selector in username_selectors:
            try:
                username_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                break
            except:
                continue
        
        if not username_field:
            logger.error("❌ Could not find username field")
            return False
        
        # Type username
        username_field.clear()
        human_delay(1, 2)
        
        logger.info("👤 Entering username...")
        for char in username:
            username_field.send_keys(char)
            time.sleep(random.uniform(0.1, 0.3))
        
        human_delay(2, 3)
        
        # Find password field
        password_field = driver.find_element(By.CSS_SELECTOR, "input[name='password']")
        password_field.clear()
        human_delay(1, 2)
        
        logger.info("🔒 Entering password...")
        for char in password:
            password_field.send_keys(char)
            time.sleep(random.uniform(0.1, 0.3))
        
        human_delay(3, 5)
        
        # Submit form
        logger.info("🚀 Submitting login...")
        try:
            login_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            driver.execute_script("arguments[0].click();", login_btn)
        except:
            password_field.send_keys(Keys.RETURN)
        
        # Wait for response
        logger.info("⏳ Waiting for login response...")
        human_delay(10, 15)
        
        # Check for success indicators
        success_indicators = [
            "//a[contains(@href, '/direct/')]",
            "//svg[@aria-label='Home']",
            "//*[@aria-label='New post']",
            "//div[@role='main']"
        ]
        
        login_success = False
        for indicator in success_indicators:
            try:
                WebDriverWait(driver, 8).until(
                    EC.presence_of_element_located((By.XPATH, indicator))
                )
                login_success = True
                logger.info(f"✅ Login success! Found indicator: {indicator}")
                break
            except:
                continue
        
        if login_success:
            # Handle post-login popups
            popup_selectors = [
                "//button[contains(text(), 'Not Now')]",
                "//button[contains(text(), 'Not now')]",
                "//button[contains(text(), 'Skip')]"
            ]
            
            for popup_selector in popup_selectors:
                try:
                    popup = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, popup_selector))
                    )
                    popup.click()
                    logger.info("✅ Popup dismissed")
                    human_delay(2, 3)
                    break
                except:
                    continue
            
            return True
        else:
            # Check for specific errors
            error_indicators = [
                "//*[contains(text(), 'incorrect')]",
                "//*[contains(text(), 'Sorry')]",
                "//*[contains(text(), 'error')]"
            ]
            
            for error_selector in error_indicators:
                try:
                    error_element = driver.find_element(By.XPATH, error_selector)
                    logger.error(f"❌ Login error: {error_element.text}")
                    break
                except:
                    continue
            
            logger.error("❌ Login failed - no success indicators found")
            
            # Take screenshot for debugging
            try:
                screenshot_path = f"login_error_{int(time.time())}.png"
                driver.save_screenshot(screenshot_path)
                logger.info(f"📸 Error screenshot saved: {screenshot_path}")
            except:
                pass
            
            return False
            
    except Exception as e:
        logger.error(f"❌ Login exception: {e}")
        return False

def upload_post(driver, file_path, caption):
    """Upload post to Instagram"""
    logger.info(f"📤 Starting upload: {os.path.basename(file_path)}")
    
    try:
        # Go to Instagram home
        driver.get("https://www.instagram.com/")
        human_delay(3, 5)
        
        # Find Create button
        create_selectors = [
            "//div[@role='menuitem']//span[text()='Create']",
            "//span[text()='Create']",
            "//svg[@aria-label='New post']",
            "//*[@aria-label='New post']"
        ]
        
        create_clicked = False
        for i, selector in enumerate(create_selectors):
            try:
                logger.info(f"🔍 Trying create selector {i+1}")
                create_btn = WebDriverWait(driver, 8).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                driver.execute_script("arguments[0].click();", create_btn)
                create_clicked = True
                logger.info("✅ Create button clicked")
                break
            except:
                continue
        
        if not create_clicked:
            logger.error("❌ Could not find Create button")
            return False
        
        human_delay(3, 5)
        
        # Upload file
        logger.info("📁 Uploading file...")
        try:
            file_input = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
            )
            
            abs_file_path = os.path.abspath(file_path)
            file_input.send_keys(abs_file_path)
            logger.info("✅ File uploaded")
            
        except Exception as e:
            logger.error(f"❌ File upload failed: {e}")
            return False
        
        human_delay(5, 8)
        
        # Click Next buttons
        logger.info("⏭️ Processing through steps...")
        for step in range(4):
            try:
                next_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Next')]"))
                )
                driver.execute_script("arguments[0].click();", next_btn)
                logger.info(f"✅ Step {step + 1} completed")
                human_delay(3, 5)
            except:
                logger.info(f"ℹ️  No more Next buttons at step {step + 1}")
                break
        
        # Add caption
        logger.info("📝 Adding caption...")
        try:
            caption_selectors = [
                "textarea[aria-label*='caption']",
                "div[contenteditable='true'][aria-label*='caption']"
            ]
            
            for selector in caption_selectors:
                try:
                    caption_area = WebDriverWait(driver, 8).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    
                    caption_area.clear()
                    human_delay(1, 2)
                    
                    # Type caption
                    for char in caption:
                        caption_area.send_keys(char)
                        time.sleep(random.uniform(0.03, 0.1))
                    
                    logger.info("✅ Caption added")
                    break
                except:
                    continue
        except:
            logger.warning("⚠️  Caption not added")
        
        human_delay(2, 4)
        
        # Share post
        logger.info("🚀 Sharing post...")
        try:
            share_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Share')]"))
            )
            driver.execute_script("arguments[0].click();", share_btn)
            logger.info("✅ Share clicked")
        except:
            logger.error("❌ Could not share post")
            return False
        
        # Wait for completion
        logger.info("⏳ Waiting for upload completion...")
        human_delay(15, 20)
        
        # Check for success (assume success if no clear failure)
        logger.info("🎉 Upload completed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Upload error: {e}")
        return False

def mark_
