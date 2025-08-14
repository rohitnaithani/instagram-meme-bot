# Use Python 3.11 slim as base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:99

# Install basic dependencies first
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    ca-certificates \
    unzip \
    xvfb \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Add Google Chrome repository and install Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/googlechrome-linux-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/googlechrome-linux-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list

RUN apt-get update && apt-get install -y \
    google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Install ChromeDriver using the new Chrome for Testing API
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d'.' -f1-3) \
    && echo "Chrome version: $CHROME_VERSION" \
    && CHROMEDRIVER_URL=$(curl -s "https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json" | \
       jq -r ".versions[] | select(.version | startswith(\"$CHROME_VERSION\")) | .downloads.chromedriver[] | select(.platform==\"linux64\") | .url" | head -1) \
    && echo "ChromeDriver URL: $CHROMEDRIVER_URL" \
    && if [ -z "$CHROMEDRIVER_URL" ]; then \
         echo "No matching ChromeDriver found, using latest stable"; \
         LATEST_VERSION=$(curl -s "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions.json" | jq -r '.channels.Stable.version'); \
         CHROMEDRIVER_URL="https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/$LATEST_VERSION/linux64/chromedriver-linux64.zip"; \
       fi \
    && wget -O /tmp/chromedriver.zip "$CHROMEDRIVER_URL" \
    && unzip /tmp/chromedriver.zip -d /tmp/ \
    && if [ -f /tmp/chromedriver-linux64/chromedriver ]; then \
         mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver; \
       else \
         mv /tmp/chromedriver /usr/local/bin/chromedriver; \
       fi \
    && chmod +x /usr/local/bin/chromedriver \
    && rm -rf /tmp/chromedriver* \
    && echo "ChromeDriver installed successfully"

# Alternative fallback method if the above fails
RUN if [ ! -f /usr/local/bin/chromedriver ]; then \
        echo "Fallback: Installing ChromeDriver via apt"; \
        apt-get update && apt-get install -y chromium-driver && \
        ln -sf /usr/bin/chromedriver /usr/local/bin/chromedriver && \
        rm -rf /var/lib/apt/lists/*; \
    fi

# Verify installations
RUN google-chrome --version
RUN chromedriver --version

# Set work directory
WORKDIR /app

# Copy requirements first (for better Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make start script executable
RUN chmod +x start.sh

# Create directories for memes
RUN mkdir -p memes/images memes/videos

# Expose port
EXPOSE 10000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:10000/health || exit 1

# Use start.sh as entrypoint
CMD ["/app/start.sh"]
