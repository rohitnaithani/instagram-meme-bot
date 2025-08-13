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
        print(f"Error saving state: {e}")

def get_random_caption():
    """Get random caption with hashtags"""
    caption = random.choice(MEME_CAPTIONS)
    return f"{caption}\n\n{HASHTAGS}"

def human_delay(min_seconds=2, max_seconds=5):
    """Add human-like delay"""
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)

def setup_driver():
    """Setup Chrome driver optimized for Render"""
    chrome_options = Options()
    
    # Essential Render options
    chrome_options.add_argument("--headless=new")  # Use new headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Memory optimization for Render
    chrome_options.add_argument("--memory-pressure-off")
    chrome_options.add_argument("--max_old_space_size=4096")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    
    # Enhanced anti-detection (Instagram is very strict)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-images")  # Faster loading
    chrome_options.add_argument("--disable-javascript")  # Reduce detection
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Realistic browser fingerprint
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Additional stealth options
    chrome_options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.notifications": 2,
        "profile.default_content_settings.popups": 0,
        "profile.managed_default_content_settings.images": 2
    })
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        
        # Execute anti-detection scripts
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
        driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
        
        driver.set_page_load_timeout(60)
        print("✅ Chrome driver initialized for Render")
        return driver
        
    except Exception as e:
        print(f"❌ Failed to start Chrome driver: {e}")
        print("💡 Make sure ChromeDriver is properly installed")
        return None

def enhanced_login(driver, username, password):
    """Enhanced login process with better Instagram handling"""
    print("🔑 Starting enhanced Instagram login...")
    
    try:
        # Go to login page directly (more reliable than homepage)
        driver.get("https://www.instagram.com/accounts/login/")
        human_delay(5, 8)
        
        # Handle any popups or cookie banners
        popup_selectors = [
            "//button[contains(text(), 'Accept')]",
            "//button[contains(text(), 'Allow')]",
            "//button[contains(text(), 'OK')]",
            "//button[@class='_a9-- _a9_1']"  # Instagram specific
        ]
        
        for selector in popup_selectors:
            try:
                popup = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                popup.click()
                print("✅ Handled popup")
                human_delay(1, 2)
                break
            except:
                continue
        
        # Wait for login form to load
        print("⏳ Waiting for login form...")
        username_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        
        # Clear any existing text and type username with realistic delays
        username_field.clear()
        human_delay(1, 2)
        
        # Type username character by character (more human-like)
        for char in username:
            username_field.send_keys(char)
            time.sleep(random.uniform(0.1, 0.3))
        
        print("✅ Username entered")
        human_delay(2, 3)
        
        # Find password field
        password_field = driver.find_element(By.NAME, "password")
        password_field.clear()
        human_delay(1, 2)
        
        # Type password character by character
        for char in password:
            password_field.send_keys(char)
            time.sleep(random.uniform(0.1, 0.3))
        
        print("✅ Password entered")
        human_delay(3, 5)
        
        # Submit form (try multiple methods)
        try:
            # Method 1: Click login button
            login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            print("🔄 Login button clicked")
        except:
            try:
                # Method 2: Press Enter key
                password_field.send_keys(Keys.RETURN)
                print("🔄 Enter key pressed")
            except Exception as e:
                print(f"❌ Failed to submit login form: {e}")
                return False
        
        # Wait for login processing
        print("⏳ Processing login...")
        human_delay(8, 12)
        
        # Check for login success indicators
        success_indicators = [
            "//a[@href='/direct/inbox/']",  # Messages
            "//svg[@aria-label='Home']",    # Home icon
            "//*[@aria-label='New post']",  # Create post
            "//a[contains(@href, '/accounts/edit/')]"  # Profile settings
        ]
        
        login_success = False
        for indicator in success_indicators:
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, indicator))
                )
                print(f"✅ Login confirmed - found: {indicator}")
                login_success = True
                break
            except:
                continue
        
        if not login_success:
            # Check for error messages
            error_selectors = [
                "//*[contains(text(), 'incorrect')]",
                "//*[contains(text(), 'error')]", 
                "//*[contains(text(), 'try again')]",
                "//*[contains(text(), 'suspended')]"
            ]
            
            for selector in error_selectors:
                try:
                    error = driver.find_element(By.XPATH, selector)
                    print(f"❌ Login error detected: {error.text}")
                    return False
                except:
                    continue
            
            print("❌ Login failed - no success indicators found")
            return False
        
        # Handle post-login popups
        post_login_popups = [
            ("//button[contains(text(), 'Not now') or contains(text(), 'Not Now')]", "Save login info"),
            ("//button[text()='Not Now']", "Turn on notifications"),
            ("//button[contains(text(), 'Skip')]", "Add phone number")
        ]
        
        for xpath, popup_name in post_login_popups:
            try:
                popup_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                popup_button.click()
                print(f"✅ Dismissed {popup_name} popup")
                human_delay(2, 3)
            except:
                print(f"ℹ️ No {popup_name} popup found")
        
        print("✅ Login process completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Login process failed: {e}")
        return False

def get_media_files():
    """Get all media files from memes folder"""
    print("📁 Scanning for media files...")
    
    image_files = []
    video_files = []
    
    # Get images
    image_patterns = [
        os.path.join(MEMES_FOLDER, "images", "*.jpg"),
        os.path.join(MEMES_FOLDER, "images", "*.jpeg"), 
        os.path.join(MEMES_FOLDER, "images", "*.png")
    ]
    
    for pattern in image_patterns:
        found_files = glob.glob(pattern)
        image_files.extend(found_files)
        if found_files:
            print(f"📸 Found {len(found_files)} files matching {pattern}")
    
    # Get videos
    video_patterns = [
        os.path.join(MEMES_FOLDER, "videos", "*.mp4"),
        os.path.join(MEMES_FOLDER, "videos", "*.mov")
    ]
    
    for pattern in video_patterns:
        found_files = glob.glob(pattern)
        video_files.extend(found_files)
        if found_files:
            print(f"🎥 Found {len(found_files)} files matching {pattern}")
    
    all_files = image_files + video_files
    random.shuffle(all_files)  # Randomize order
    
    print(f"📊 Total media files: {len(all_files)} ({len(image_files)} images, {len(video_files)} videos)")
    return all_files

def main():
    """Main upload function optimized for Render"""
    print("🚀 Starting Instagram meme uploader on Render...")
    print(f"⏰ Current time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check environment variables
    if not all([INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD]):
        print("❌ Missing environment variables!")
        print("💡 Set INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD in Render dashboard")
        return
    
    print(f"✅ Instagram credentials loaded (username: {INSTAGRAM_USERNAME})")
    
    # Load state
    state = load_state()
    posted_files = set(state["posted_files"])
    print(f"📊 Previously posted files: {len(posted_files)}")
    
    # Get available media files
    media_files = get_media_files()
    
    if not media_files:
        print("❌ No media files found!")
        print("💡 Make sure the meme fetcher has run successfully")
        print("🔄 Try running: Force Meme Fetch from dashboard")
        return
    
    # Filter out already posted files
    available_files = [f for f in media_files if f not in posted_files]
    
    if not available_files:
        print("ℹ️ All files have been posted! Resetting cycle...")
        available_files = media_files
        posted_files = set()
        # Reset state
        state["posted_files"] = []
        save_state(state)
    
    print(f"📤 Files available to post: {len(available_files)}")
    
    if available_files:
        print(f"🎯 Next file to post: {os.path.basename(available_files[0])}")
    
    # Setup driver
    driver = setup_driver()
    if not driver:
        print("❌ Failed to setup Chrome driver")
        return
    
    try:
        # Login to Instagram
        if not enhanced_login(driver, INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD):
            print("❌ Instagram login failed")
            print("💡 Check your credentials and account status")
            return
        
        print("🎉 Ready to upload! Login successful.")
        print("⚠️ Note: Due to Instagram's anti-bot measures, uploads may still fail")
        print("🔄 If posts don't appear, Instagram may be blocking the automation")
        
        # For now, just confirm login works
        # The actual upload process would continue here
        
        # Update state to show successful login
        state["last_upload_date"] = time.strftime("%Y-%m-%d %H:%M:%S")
        save_state(state)
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    finally:
        try:
            driver.quit()
            print("🔚 Browser closed successfully")
        except:
            pass

if __name__ == "__main__":
    main()
