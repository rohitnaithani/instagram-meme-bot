#!/bin/bash
echo "🚀 Starting Instagram Meme Bot on Render..."
echo "📅 Current time: $(date)"

# Check if Chrome is installed
if command -v google-chrome &> /dev/null; then
    echo "✅ Chrome installed: $(google-chrome --version)"
else
    echo "❌ Chrome not found!"
fi

# Check if ChromeDriver is installed
if command -v chromedriver &> /dev/null; then
    echo "✅ ChromeDriver installed: $(chromedriver --version)"
else
    echo "❌ ChromeDriver not found!"
fi

# Check Python version
echo "✅ Python version: $(python --version)"

# Start the scheduler (this is the correct filename)
echo "🚀 Starting scheduler_main.py..."
python scheduler_main.py
