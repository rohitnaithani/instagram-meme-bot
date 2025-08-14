#!/bin/bash
echo "🚀 Starting Instagram Meme Bot on Render..."
echo "📅 Current time: $(date)"
echo "================================================"

# Environment check
echo "🔍 Environment Check:"
echo "   INSTAGRAM_USERNAME: ${INSTAGRAM_USERNAME:+SET}"
echo "   INSTAGRAM_PASSWORD: ${INSTAGRAM_PASSWORD:+SET}"
echo "   DATABASE_URL: ${DATABASE_URL:+SET}"
echo "   REDDIT_CLIENT_ID: ${REDDIT_CLIENT_ID:+SET}"

# List files to verify what we have
echo "📁 Files in /app:"
ls -la /app/*.py

# Check if Chrome is installed and get version
if command -v google-chrome &> /dev/null; then
    CHROME_VERSION=$(google-chrome --version)
    echo "✅ Chrome installed: $CHROME_VERSION"
    
    # Test Chrome with basic flags
    echo "🧪 Testing Chrome startup..."
    timeout 10s google-chrome --headless --no-sandbox --disable-dev-shm-usage --version 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "✅ Chrome basic test passed"
    else
        echo "⚠️  Chrome basic test failed"
    fi
else
    echo "❌ Chrome not found!"
    echo "   Available browsers:"
    ls -la /usr/bin/ | grep -i chrome || echo "   No Chrome found"
fi

# Check ChromeDriver (webdriver-manager will handle this)
echo "🚗 ChromeDriver will be managed by webdriver-manager"

# Check Python version and packages
echo "✅ Python version: $(python --version)"
echo "📦 Checking key packages:"
python -c "import selenium; print(f'   Selenium: {selenium.__version__}')" 2>/dev/null || echo "   ❌ Selenium not found"
python -c "import psycopg2; print('   ✅ psycopg2 available')" 2>/dev/null || echo "   ❌ psycopg2 not found"
python -c "import praw; print('   ✅ praw available')" 2>/dev/null || echo "   ❌ praw not found"

# Check database connectivity
if [ ! -z "$DATABASE_URL" ]; then
    echo "🔌 Testing database connection..."
    python -c "
import psycopg2
import os
try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    print('   ✅ Database connection successful')
    conn.close()
except Exception as e:
    print(f'   ❌ Database connection failed: {e}')
" 2>/dev/null
else
    echo "   ⚠️  DATABASE_URL not set"
fi

# Start Xvfb for headless display (if needed)
echo "🖥️  Starting virtual display..."
Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99

echo "================================================"
echo "🚀 Starting scheduler_main.py..."
python scheduler_main.py
