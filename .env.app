# CoderDojo Guide Generator Configuration

# Output settings (subdirectories within OUTPUT_ROOT_DIR)
OUTPUT_DIR="Projects"
CACHE_DIR="cache"
LOG_DIR="logs"

# Scraping settings
RATE_LIMIT_SECONDS=2
BROWSER_HEADLESS=true
BROWSER_TIMEOUT=50000

# Logging
LOG_LEVEL="INFO"
LOG_FORMAT="%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Image settings
IMAGE_DOWNLOAD_TIMEOUT=60
IMAGE_OUTPUT_DIR="images"
IMAGE_SCALE=1.2

# Enhancement settings (Upscayl)
UPSCAYL_PATH="C:\Program Files\Upscayl\resources\bin\upscayl-bin.exe"
UPSCAYL_SCALE=4
UPSCAYL_MODEL="upscayl-standard-4x"
ENHANCE_IMAGES=true

# GPU settings (for multi-GPU systems)
# UPSCAYL_GPU_ID=auto      # auto, 0, 1, or "0,1" for multi-GPU
# UPSCAYL_THREADS=1:2:2    # load:proc:save thread counts

# QR Code settings
QRCODE_SCALE=0.5

# Translation settings
TRANSLATE_ENABLED=true
TRANSLATION_SOURCE="en"
TRANSLATION_TARGET="nl"
TRANSLATION_PROVIDER=google

