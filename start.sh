#!/bin/bash
echo "🚀 Starting Instagram Meme Bot on Render..."
echo "📅 Current time: $(date)"

# List files to verify what we have
echo "📁 Files in /app:"
ls -la /app/*.py

# Check if Chrome is installed
if command -v google-chrome &> /dev/null; then
    echo "✅ Chrome installed: $(google-chrome --version)"
else
    echo "❌ Chrome not found!"
fi

# Check Python version
echo "✅ Python version: $(python --version)"

# Start the scheduler (correct filename)
echo "🚀 Starting scheduler_main.py..."
python scheduler_main.py
