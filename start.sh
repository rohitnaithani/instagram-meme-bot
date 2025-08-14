#!/bin/bash
echo "🚀 Starting Instagram Meme Bot..."
echo "📅 $(date)"

# Basic environment check
echo "🔍 Environment Check:"
echo "   INSTAGRAM_USERNAME: ${INSTAGRAM_USERNAME:+SET}"
echo "   DATABASE_URL: ${DATABASE_URL:+SET}"

# Check if Chrome is installed
if command -v google-chrome &> /dev/null; then
    echo "✅ Chrome installed: $(google-chrome --version)"
else
    echo "❌ Chrome not found!"
fi

# Check Python
echo "✅ Python: $(python --version)"

# Test database connection quickly
if [ ! -z "$DATABASE_URL" ]; then
    python -c "
import psycopg2
import os
try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    print('✅ Database connection successful')
    conn.close()
except Exception as e:
    print(f'❌ Database connection failed: {e}')
" 2>/dev/null
fi

echo "🚀 Starting main application..."
python scheduler_main.py
