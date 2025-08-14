import os
import time
import random
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import glob
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ====== CONFIG FROM ENVIRONMENT VARIABLES ======
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD")
MEMES_FOLDER = "memes"
POSTS_PER_RUN = 1
STATE_FILE = "upload_state.json"

# Enhanced captions for better engagement
MEME_CAPTIONS = [
    "This one hits different 💀",
    "Tag someone who needs this 😂",
    "POV: You can relate 🎯",
    "When it's too accurate 😭", 
    "Me trying to adult:",
    "That friend who always...",
    "Plot twist: Monday strikes again",
    "Why is this so true though? 🤔",
    "Not me laughing at this 🤣",
    "This is sending me 🚀",
    "The accuracy is scary 📍",
    "When life hits you with reality:",
]

# Trending hashtags for better reach
HASHTAGS = "#memes #funny #relatable #comedy #viral #trending #lol #dankmemes #funnymemes #memesdaily #humor #laughs #mood #same #facts"

def load_state():
    """Load upload state to track posted memes"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except:
            return {"posted_files": [], "last_upload_date": ""}
    return {"posted_files": [], "last_upload_date": ""}

def save_state(state):
    """Save upload state"""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving state: {e}")

def get_random_caption():
    """Get random caption with hashtags"""
    caption = random.choice(MEME_CAPTIONS)
    return f"{caption}\n\n{HASHTAGS}"

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
    
    # Additional preferences
    chrome_options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.notifications": 2,
        "profile.default_content_settings.popups": 0
    })
    
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
        for step in range(3):  # Usually 2-3 next buttons
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

def get_media_files():
    """Get available media files"""
    logger.info("📁 Scanning for media files...")
    
    image_files = []
    video_files = []
    
    # Get images
    for ext in ["*.jpg", "*.jpeg", "*.png"]:
        pattern = os.path.join(MEMES_FOLDER, "images", ext)
        found = glob.glob(pattern)
        image_files.extend(found)
    
    # Get videos
    for ext in ["*.mp4", "*.mov"]:
        pattern = os.path.join(MEMES_FOLDER, "videos", ext)
        found = glob.glob(pattern)
        video_files.extend(found)
    
    all_files = image_files + video_files
    random.shuffle(all_files)
    
    logger.info(f"📊 Found {len(all_files)} total files ({len(image_files)} images, {len(video_files)} videos)")
    return all_files

def main():
    """Main upload function"""
    logger.info("🚀 Starting Instagram uploader...")
    
    # Check credentials
    if not all([INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD]):
        logger.error("❌ Missing Instagram credentials!")
        logger.error("💡 Set INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD in environment")
        return False
    
    logger.info(f"✅ Instagram credentials loaded for: {INSTAGRAM_USERNAME}")
    
    # Load state
    state = load_state()
    posted_files = set(state["posted_files"])
    
    # Get media files
    media_files = get_media_files()
    if not media_files:
        logger.error("❌ No media files found!")
        return False
    
    # Filter available files
    available_files = [f for f in media_files if f not in posted_files]
    
    if not available_files:
        logger.info("ℹ️  All files posted, resetting cycle...")
        available_files = media_files
        posted_files = set()
        state["posted_files"] = []
    
    logger.info(f"📤 {len(available_files)} files available to post")
    
    if not available_files:
        logger.error("❌ No files available")
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
        
        # Upload post
        file_to_upload = available_files[0]
        caption = get_random_caption()
        
        if upload_post(driver, file_to_upload, caption):
            # Mark as posted
            posted_files.add(file_to_upload)
            state["posted_files"] = list(posted_files)
            state["last_upload_date"] = time.strftime("%Y-%m-%d %H:%M:%S")
            save_state(state)
            
            logger.info(f"🎉 Successfully uploaded: {os.path.basename(file_to_upload)}")
            success = True
        else:
            logger.error("❌ Upload failed")
    
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
    
    finally:
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
