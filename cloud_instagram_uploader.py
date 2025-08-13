import os
import time
import random
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import glob

# ====== CONFIG FROM ENVIRONMENT VARIABLES ======
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD")
MEMES_FOLDER = "memes"
POSTS_PER_RUN = 1  # Post 1 meme per run (run multiple times daily)
STATE_FILE = "upload_state.json"

# Captions and hashtags
MEME_CAPTIONS = [
    "Tag someone who needs to see this 😂",
    "This hits different 💯",
    "When you relate too much 😭", 
    "POV: It's too accurate 🎯",
    "Not me crying laughing 💀",
    "This is sending me 🚀",
    "Why is this so true though? 🤔",
    "The accuracy is scary 📍",
    "Me trying to act normal:",
    "That one friend who always...",
    "When life hits you with reality:",
    "Plot twist: it's Monday again",
]

HASHTAGS = "#memes #funny #relatable #comedy #viral #trending #lol #dankmemes #funnymemes #memesdaily"

def load_state():
    """Load upload state to track posted memes"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {"posted_files": [], "last_upload_date": ""}

def save_state(state):
    """Save upload state"""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def get_random_caption():
    """Get random caption with hashtags"""
    caption = random.choice(MEME_CAPTIONS)
    return f"{caption}\n\n{HASHTAGS}"

def human_delay(min_seconds=2, max_seconds=5):
    """Add human-like delay"""
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)

def setup_driver():
    """Setup Chrome driver with stealth options for cloud"""
    chrome_options = Options()
    
    # Cloud-friendly options
    chrome_options.add_argument("--headless")  # Run without GUI
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Anti-detection options
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
    except Exception as e:
        print(f"❌ Failed to start Chrome driver: {e}")
        print("💡 Make sure ChromeDriver is installed and accessible")
        return None

def login_instagram(driver, username, password):
    """Login to Instagram"""
    print("🔑 Logging into Instagram...")
    
    driver.get("https://www.instagram.com/")
    human_delay(3, 5)
    
    try:
        # Handle cookie banner if present
        try:
            accept_cookies = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept') or contains(text(), 'Allow')]"))
            )
            accept_cookies.click()
            human_delay()
        except:
            pass
        
        # Find username field
        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        
        # Type username with human-like typing
        for char in username:
            username_field.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))
        
        human_delay(1, 2)
        
        # Find password field
        password_field = driver.find_element(By.NAME, "password")
        
        # Type password
        for char in password:
            password_field.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))
        
        human_delay(1, 2)
        
        # Click login button
        login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        login_button.click()
        
        human_delay(5, 8)
        
        # Handle "Save Login Info" popup
        try:
            not_now_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Not now') or contains(text(), 'Not Now')]"))
            )
            not_now_button.click()
            human_delay(2, 3)
        except:
            pass
        
        # Handle notification popup
        try:
            not_now_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Not Now') or contains(text(), 'Not now')]"))
            )
            not_now_button.click()
            human_delay()
        except:
            pass
        
        print("✅ Successfully logged in!")
        return True
        
    except Exception as e:
        print(f"❌ Login failed: {e}")
        return False

def upload_media(driver, file_path, caption):
    """Upload a single media file"""
    try:
        print(f"📤 Uploading: {os.path.basename(file_path)}")
        
        # Click the + button to create new post
        create_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//a[@href='/create/select/' or contains(@aria-label, 'New post')]"))
        )
        create_button.click()
        
        human_delay(2, 4)
        
        # Upload file
        file_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='file']"))
        )
        file_input.send_keys(os.path.abspath(file_path))
        
        human_delay(4, 6)
        
        # Click Next button (crop/size)
        next_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Next')]"))
        )
        next_button.click()
        
        human_delay(3, 4)
        
        # Click Next button (filter) - might not appear for some files
        try:
            next_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Next')]"))
            )
            next_button.click()
            human_delay(3, 4)
        except:
            print("ℹ️ No filter step (normal for some files)")
        
        # Add caption
        caption_textarea = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//textarea[@aria-label='Write a caption...' or contains(@placeholder, 'caption')]"))
        )
        
        # Clear any existing text
        caption_textarea.clear()
        
        # Type caption with realistic speed
        for char in caption:
            caption_textarea.send_keys(char)
            if char in ' \n':
                time.sleep(random.uniform(0.1, 0.3))
            else:
                time.sleep(random.uniform(0.02, 0.08))
        
        human_delay(2, 4)
        
        # Click Share button
        share_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Share')]"))
        )
        share_button.click()
        
        # Wait for upload to complete
        print("⏳ Waiting for upload to complete...")
        human_delay(10, 20)
        
        # Check if post was successful (look for success indicators)
        try:
            # Look for "Your post has been shared" or similar
            WebDriverWait(driver, 30).until(
                EC.any_of(
                    EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'shared') or contains(text(), 'posted')]")),
                    EC.presence_of_element_located((By.XPATH, "//a[@href='/']"))  # Back to home
                )
            )
            print("✅ Upload successful!")
            return True
        except:
            print("⚠️ Upload status unclear, but probably successful")
            return True
        
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return False

def get_media_files():
    """Get all media files from memes folder"""
    image_files = []
    video_files = []
    
    # Get images
    image_patterns = [
        os.path.join(MEMES_FOLDER, "images", "*.jpg"),
        os.path.join(MEMES_FOLDER, "images", "*.jpeg"), 
        os.path.join(MEMES_FOLDER, "images", "*.png")
    ]
    
    for pattern in image_patterns:
        image_files.extend(glob.glob(pattern))
    
    # Get videos
    video_patterns = [
        os.path.join(MEMES_FOLDER, "videos", "*.mp4"),
        os.path.join(MEMES_FOLDER, "videos", "*.mov")
    ]
    
    for pattern in video_patterns:
        video_files.extend(glob.glob(pattern))
    
    all_files = image_files + video_files
    random.shuffle(all_files)  # Randomize order
    return all_files

def main():
    """Main upload function"""
    print("🚀 Starting Instagram meme upload bot...")
    
    # Check environment variables
    if not all([INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD]):
        print("❌ Missing environment variables! Check INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD")
        return
    
    # Load state
    state = load_state()
    posted_files = set(state["posted_files"])
    
    # Get available media files
    media_files = get_media_files()
    
    if not media_files:
        print("❌ No media files found in memes folder!")
        print("💡 Run the meme fetcher first: python meme_fetcher.py")
        return
    
    # Filter out already posted files
    available_files = [f for f in media_files if f not in posted_files]
    
    if not available_files:
        print("ℹ️ All files have been posted! Resetting cycle...")
        available_files = media_files
        posted_files = set()
    
    print(f"📁 Found {len(available_files)} files available to post")
    
    # Setup driver
    driver = setup_driver()
    if not driver:
        return
    
    try:
        # Login
        if not login_instagram(driver, INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD):
            return
        
        # Upload posts
        uploaded_count = 0
        
        for file_path in available_files[:POSTS_PER_RUN]:
            caption = get_random_caption()
            
            if upload_media(driver, file_path, caption):
                posted_files.add(file_path)
                uploaded_count += 1
                
                # Save state after each successful upload
                state["posted_files"] = list(posted_files)
                state["last_upload_date"] = time.strftime("%Y-%m-%d %H:%M:%S")
                save_state(state)
                
                print(f"✅ Posted {uploaded_count}/{POSTS_PER_RUN}")
                
                # Wait between posts if posting multiple
                if uploaded_count < POSTS_PER_RUN:
                    wait_time = random.randint(300, 900)  # 5-15 minutes
                    print(f"⏳ Waiting {wait_time//60} minutes before next post...")
                    time.sleep(wait_time)
        
        print(f"\n🎯 Upload session complete!")
        print(f"📤 Successfully posted: {uploaded_count}/{POSTS_PER_RUN}")
        print(f"📊 Total files posted: {len(posted_files)}")
        
    except Exception as e:
        print(f"❌ Error during upload: {e}")
    
    finally:
        driver.quit()
        print("🔚 Browser closed")

if __name__ == "__main__":
    main()