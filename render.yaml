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
import traceback

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

def detailed_debug_info():
    """Print detailed debug information for troubleshooting"""
    print("=" * 60)
    print("🔍 DETAILED DEBUG INFORMATION")
    print("=" * 60)
    
    # Environment check
    print(f"📍 Current working directory: {os.getcwd()}")
    print(f"🐍 Python executable: {os.sys.executable}")
    print(f"⏰ Current time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check environment variables (safely)
    env_vars = ["INSTAGRAM_USERNAME", "INSTAGRAM_PASSWORD", "REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET"]
    for var in env_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: Set (length {len(value)})")
        else:
            print(f"❌ {var}: Not set")
    
    # Check files
    print(f"\n📁 Files in current directory:")
    try:
        for item in os.listdir('.'):
            if os.path.isfile(item):
                size = os.path.getsize(item)
                print(f"   📄 {item} ({size} bytes)")
            else:
                print(f"   📁 {item}/")
    except Exception as e:
        print(f"   ❌ Error listing files: {e}")
    
    # Check memes folder
    print(f"\n🎭 Memes folder structure:")
    memes_path = MEMES_FOLDER
    if os.path.exists(memes_path):
        for root, dirs, files in os.walk(memes_path):
            level = root.replace(memes_path, '').count(os.sep)
            indent = '  ' * level
            print(f"{indent}📁 {os.path.basename(root)}/")
            subindent = '  ' * (level + 1)
            for file in files:
                file_path = os.path.join(root, file)
                size = os.path.getsize(file_path)
                print(f"{subindent}📄 {file} ({size} bytes)")
    else:
        print("   ❌ Memes folder not found!")
    
    # System info
    print(f"\n💻 System Information:")
    print(f"   Platform: {os.sys.platform}")
    
    # Check Chrome installation
    chrome_paths = ["/usr/bin/google-chrome", "/usr/bin/chromium", "/opt/google/chrome/chrome"]
    chrome_found = False
    for path in chrome_paths:
        if os.path.exists(path):
            print(f"   ✅ Chrome found at: {path}")
            chrome_found = True
            # Try to get version
            try:
                import subprocess
                result = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    print(f"   📊 Version: {result.stdout.strip()}")
            except Exception as e:
                print(f"   ⚠️ Could not get version: {e}")
            break
    
    if not chrome_found:
        print("   ❌ Chrome not found in standard locations")
    
    # Check ChromeDriver
    chromedriver_paths = ["/usr/local/bin/chromedriver", "/usr/bin/chromedriver"]
    driver_found = False
    for path in chromedriver_paths:
        if os.path.exists(path):
            print(f"   ✅ ChromeDriver found at: {path}")
            driver_found = True
            break
    
    if not driver_found:
        print("   ❌ ChromeDriver not found in standard locations")
    
    # Memory info (if available)
    try:
        import psutil
        memory = psutil.virtual_memory()
        print(f"   💾 Available memory: {memory.available / (1024**3):.2f} GB")
        print(f"   💾 Memory usage: {memory.percent}%")
    except ImportError:
        print("   ℹ️ psutil not available for memory info")
    
    print("=" * 60)

def load_state():
    """Load upload state to track posted memes"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                data = json.load(f)
                print(f"📊 Loaded state: {len(data.get('posted_files', []))} posted files")
                return data
        except Exception as e:
            print(f"❌ Error loading state: {e}")
            return {"posted_files": [], "last_upload_date": ""}
    print("ℹ️ No previous state file found")
    return {"posted_files": [], "last_upload_date": ""}

def save_state(state):
    """Save upload state"""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
        print(f"💾 State saved: {len(state.get('posted_files', []))} total posts")
    except Exception as e:
        print(f"❌ Error saving state: {e}")

def setup_driver():
    """Setup Chrome driver optimized for Render with better error handling"""
    print("🔧 Setting up Chrome driver for Render...")
    
    chrome_options = Options()
    
    # Essential Render options
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Memory optimization
    chrome_options.add_argument("--memory-pressure-off")
    chrome_options.add_argument("--max_old_space_size=2048")  # Reduced for Render
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    
    # FIXED: Removed problematic options that break Instagram
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    # REMOVED: --disable-javascript and --disable-images (these break Instagram!)
    
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Realistic user agent
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Additional preferences
    chrome_options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.notifications": 2,
        "profile.default_content_settings.popups": 0,
    })
    
    # Render-specific stability options
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    chrome_options.add_argument("--disable-ipc-flooding-protection")
    
    try:
        print("🚀 Attempting to create Chrome WebDriver...")
        driver = webdriver.Chrome(options=chrome_options)
        
        # Anti-detection scripts
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
        driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
        
        driver.set_page_load_timeout(60)
        print("✅ Chrome driver initialized successfully")
        
        # Test basic functionality
        try:
            print("🧪 Testing driver with Google homepage...")
            driver.get("https://www.google.com")
            title = driver.title
            print(f"✅ Test successful - page title: {title}")
            return driver
        except Exception as e:
            print(f"❌ Driver test failed: {e}")
            driver.quit()
            return None
        
    except Exception as e:
        print(f"❌ Failed to create Chrome driver: {e}")
        print(f"📋 Full error details: {traceback.format_exc()}")
        
        # Additional diagnostics
        print("\n🔍 Driver creation diagnostics:")
        
        # Check if ChromeDriver executable exists
        try:
            import subprocess
            result = subprocess.run(["which", "chromedriver"], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ ChromeDriver found at: {result.stdout.strip()}")
            else:
                print("❌ ChromeDriver not found in PATH")
        except:
            pass
        
        # Check if Chrome executable exists
        try:
            result = subprocess.run(["which", "google-chrome"], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Chrome found at: {result.stdout.strip()}")
            else:
                print("❌ Chrome not found in PATH")
        except:
            pass
        
        return None

def get_media_files():
    """Get all media files from memes folder with detailed logging"""
    print("🔍 Scanning for media files...")
    
    image_files = []
    video_files = []
    
    # Ensure directories exist
    os.makedirs(f"{MEMES_FOLDER}/images", exist_ok=True)
    os.makedirs(f"{MEMES_FOLDER}/videos", exist_ok=True)
    
    # Get images
    image_patterns = [
        os.path.join(MEMES_FOLDER, "images", "*.jpg"),
        os.path.join(MEMES_FOLDER, "images", "*.jpeg"), 
        os.path.join(MEMES_FOLDER, "images", "*.png")
    ]
    
    for pattern in image_patterns:
        try:
            found_files = glob.glob(pattern)
            if found_files:
                print(f"📸 Found {len(found_files)} files matching {pattern}")
                for file in found_files:
                    size = os.path.getsize(file)
                    print(f"   - {os.path.basename(file)} ({size} bytes)")
            image_files.extend(found_files)
        except Exception as e:
            print(f"❌ Error scanning {pattern}: {e}")
    
    # Get videos
    video_patterns = [
        os.path.join(MEMES_FOLDER, "videos", "*.mp4"),
        os.path.join(MEMES_FOLDER, "videos", "*.mov")
    ]
    
    for pattern in video_patterns:
        try:
            found_files = glob.glob(pattern)
            if found_files:
                print(f"🎥 Found {len(found_files)} files matching {pattern}")
                for file in found_files:
                    size = os.path.getsize(file)
                    print(f"   - {os.path.basename(file)} ({size} bytes)")
            video_files.extend(found_files)
        except Exception as e:
            print(f"❌ Error scanning {pattern}: {e}")
    
    all_files = image_files + video_files
    random.shuffle(all_files)
    
    print(f"📊 Total media files found: {len(all_files)} ({len(image_files)} images, {len(video_files)} videos)")
    return all_files

def test_instagram_access(driver):
    """Test if we can access Instagram at all"""
    print("🧪 Testing Instagram accessibility...")
    
    try:
        driver.get("https://www.instagram.com/")
        time.sleep(5)
        
        title = driver.title
        print(f"📄 Page title: {title}")
        
        # Check if we got redirected or blocked
        current_url = driver.current_url
        print(f"🔗 Current URL: {current_url}")
        
        if "instagram.com" not in current_url:
            print("❌ Got redirected away from Instagram!")
            return False
            
        # Look for login elements
        try:
            login_link = driver.find_element(By.XPATH, "//a[contains(@href, '/accounts/login/')]")
            print("✅ Found login link - Instagram is accessible")
            return True
        except:
            # Maybe already on login page
            try:
                username_field = driver.find_element(By.NAME, "username")
                print("✅ Found login form - Instagram is accessible")
                return True
            except:
                print("⚠️ Instagram accessible but login elements not found")
                print(f"📋 Page source preview: {driver.page_source[:500]}...")
                return False
                
    except Exception as e:
        print(f"❌ Instagram accessibility test failed: {e}")
        return False

def main():
    """Main upload function with comprehensive error handling"""
    print("🚀 Starting Instagram Meme Uploader...")
    print(f"⏰ Execution time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run detailed diagnostics
    detailed_debug_info()
    
    # Validate environment
    if not all([INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD]):
        print("❌ CRITICAL: Missing Instagram credentials!")
        print("💡 Set INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD environment variables")
        return False
    
    print(f"✅ Instagram credentials loaded for: {INSTAGRAM_USERNAME}")
    
    # Check for media files first
    media_files = get_media_files()
    if not media_files:
        print("❌ CRITICAL: No media files found!")
        print("💡 Make sure the meme fetcher has downloaded files to memes/images/ and memes/videos/")
        print("🔄 Try running the meme fetcher first")
        return False
    
    # Load upload state
    state = load_state()
    posted_files = set(state.get("posted_files", []))
    
    # Filter available files
    available_files = [f for f in media_files if f not in posted_files]
    if not available_files:
        print("ℹ️ All files have been posted - resetting cycle")
        available_files = media_files
        posted_files = set()
        state = {"posted_files": [], "last_upload_date": ""}
    
    print(f"📤 Ready to upload from {len(available_files)} available files")
    if available_files:
        next_file = available_files[0]
        print(f"🎯 Next file: {os.path.basename(next_file)} ({os.path.getsize(next_file)} bytes)")
    
    # Setup Chrome driver
    driver = setup_driver()
    if not driver:
        print("❌ CRITICAL: Failed to setup Chrome driver")
        print("💡 This is likely a Render environment issue")
        return False
    
    try:
        # Test Instagram accessibility
        if not test_instagram_access(driver):
            print("❌ CRITICAL: Cannot access Instagram")
            return False
        
        print("🎉 SUCCESS: Environment setup complete!")
        print("🔑 Next step would be Instagram login...")
        
        # Update state to show we got this far
        state["last_attempt"] = time.strftime("%Y-%m-%d %H:%M:%S")
        state["setup_successful"] = True
        save_state(state)
        
        print("✅ Upload preparation completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        print(f"📋 Full traceback: {traceback.format_exc()}")
        return False
        
    finally:
        try:
            driver.quit()
            print("🔚 Browser closed")
        except:
            pass

if __name__ == "__main__":
    success = main()
    if success:
        print("🎉 Script completed successfully")
        exit(0)
    else:
        print("❌ Script failed")
        exit(1)
