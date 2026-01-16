# CoderDojo Guide Generator Configuration

# Output settings
OUTPUT_DIR="./output"
CACHE_DIR="./cache"

# Scraping settings
RATE_LIMIT_SECONDS=2
BROWSER_HEADLESS=true
BROWSER_TIMEOUT=30000

# Logging
LOG_LEVEL="INFO"
LOG_FORMAT="%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Image settings
IMAGE_DOWNLOAD_TIMEOUT=30
IMAGE_OUTPUT_DIR="images"

# Enhancement settings (Upscayl)
UPSCAYL_PATH="C:\Program Files\Upscayl\resources\bin\upscayl-bin.exe"
UPSCAYL_SCALE=4
UPSCAYL_MODEL="upscayl-standard-4x"
ENHANCE_IMAGES=true

# Translation settings
TRANSLATE_ENABLED=true
TRANSLATION_SOURCE="en"
TRANSLATION_TARGET="nl"
