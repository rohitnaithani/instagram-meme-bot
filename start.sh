#!/bin/bash
echo "🚀 Starting Instagram Meme Bot..."
echo "📅 $(date)"

# Basic environment check
echo "🔍 Environment Check:"
echo "   INSTAGRAM_USERNAME: ${INSTAGRAM_USERNAME:+SET}"
echo "   DATABASE_URL: ${DATABASE_URL:+SET}"

# Check Chrome installation
echo "🌐 Browser Check:"
if command -v google-chrome &> /dev/null; then
    CHROME_VERSION=$(google-chrome --version 2>/dev/null || echo "Version check failed")
    echo "   ✅ Chrome: $CHROME_VERSION"
else
    echo "   ❌ Chrome not found!"
    exit 1
fi

# Check ChromeDriver
if command -v chromedriver &> /dev/null; then
    CHROMEDRIVER_VERSION=$(chromedriver --version 2>/dev/null || echo "Version check failed")
    echo "   ✅ ChromeDriver: $CHROMEDRIVER_VERSION"
    
    # Verify ChromeDriver is executable
    if [ -x "/usr/local/bin/chromedriver" ]; then
        echo "   ✅ ChromeDriver is executable"
    else
        echo "   ⚠️  ChromeDriver permissions issue, fixing..."
        chmod +x /usr/local/bin/chromedriver
    fi
else
    echo "   ❌ ChromeDriver not found!"
    echo "   💡 Expected at /usr/local/bin/chromedriver"
    ls -la /usr/local/bin/chrome* 2>/dev/null || echo "   No chrome binaries found"
    exit 1
fi

# Check Python and dependencies
echo "🐍 Python Check:"
echo "   Python: $(python --version)"

# Quick dependency check
python -c "
import selenium
import psycopg2
import praw
print('   ✅ All Python dependencies available')
print(f'   Selenium: {selenium.__version__}')
print(f'   psycopg2: {psycopg2.__version__}')
print(f'   praw: {praw.__version__}')
" 2>/dev/null || echo "   ⚠️  Some Python dependencies missing"

# Test database connection
if [ ! -z "$DATABASE_URL" ]; then
    echo "🗄️  Database Check:"
    python -c "
import psycopg2
import os
try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()
    cursor.execute('SELECT version();')
    version = cursor.fetchone()[0]
    print(f'   ✅ PostgreSQL: {version[:50]}...')
    
    # Check if memes table exists
    cursor.execute(\"SELECT to_regclass('public.memes');\")
    table_exists = cursor.fetchone()[0]
    if table_exists:
        cursor.execute('SELECT COUNT(*) FROM memes;')
        count = cursor.fetchone()[0]
        print(f'   ✅ Memes table: {count} records')
    else:
        print('   ⚠️  Memes table not found')
    
    conn.close()
except Exception as e:
    print(f'   ❌ Database error: {e}')
" 2>/dev/null
else
    echo "🗄️  Database Check: ❌ DATABASE_URL not set"
fi

# Test Chrome setup with a quick run
echo "🧪 Chrome Test:"
timeout 30s python -c "
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import subprocess

try:
    # Check versions match
    chrome_result = subprocess.run(['google-chrome', '--version'], capture_output=True, text=True)
    driver_result = subprocess.run(['chromedriver', '--version'], capture_output=True, text=True)
    
    print(f'   Chrome: {chrome_result.stdout.strip()}')
    print(f'   Driver: {driver_result.stdout.strip()}')
    
    # Quick driver test
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    service = Service('/usr/local/bin/chromedriver')
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get('data:text/html,<html><body><h1>Test</h1></body></html>')
    
    if 'Test' in driver.page_source:
        print('   ✅ Chrome driver test passed')
    else:
        print('   ❌ Chrome driver test failed')
    
    driver.quit()
    
except Exception as e:
    print(f'   ❌ Chrome test failed: {e}')
" 2>/dev/null || echo "   ❌ Chrome test timed out or failed"

echo ""
echo "🚀 All checks complete. Starting main application..."
echo "📊 Dashboard will be available at your Render URL"
echo ""

# Start the main application
exec python scheduler_main.py
