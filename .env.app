# CoderDojo Guide Generator Configuration

# Output settings
OUTPUT_DIR="./output"
CACHE_DIR="./cache"
LOG_DIR=logs  

# Scraping settings
RATE_LIMIT_SECONDS=2
BROWSER_HEADLESS=true
BROWSER_TIMEOUT=50000

# Logging
LOG_LEVEL="INFO"
LOG_FORMAT="%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Image settings
IMAGE_DOWNLOAD_TIMEOUT=30
IMAGE_OUTPUT_DIR="images"
IMAGE_SCALE=1.2

# Enhancement settings (Upscayl)
UPSCAYL_PATH="C:\Program Files\Upscayl\resources\bin\upscayl-bin.exe"
UPSCAYL_SCALE=4
UPSCAYL_MODEL="upscayl-standard-4x"
ENHANCE_IMAGES=true

# QR Code settings
QRCODE_SCALE=0.5

# Translation settings
TRANSLATE_ENABLED=true
TRANSLATION_SOURCE="en"
TRANSLATION_TARGET="nl"
