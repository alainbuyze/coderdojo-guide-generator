# CoderDojo Guide Generator

Create printable Dutch instruction guides from online maker kit tutorials.

This tool automatically downloads tutorials from supported websites, translates them to Dutch, enhances images for print quality, and generates ready-to-print Markdown guides.

## Features

- **Web Scraping**: Fetches tutorial pages using Playwright (handles JavaScript-rendered content)
- **Content Extraction**: Extracts structured content (title, sections, images) using BeautifulSoup
- **Image Downloading**: Downloads all images locally for offline printing
- **Image Enhancement**: Optional 4x upscaling using Upscayl for better print quality
- **Dutch Translation**: Automatic translation using Google Translate (via deep-translator)
- **Markdown Output**: Generates clean Markdown files ready for printing

## Requirements

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- [Upscayl](https://github.com/upscayl/upscayl) (optional, for image enhancement)

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd Coderdojo
```

### 2. Install dependencies

Using uv (recommended):
```bash
uv sync
```

Or using pip:
```bash
pip install -e .
```

### 3. Install Playwright browser

```bash
uv run playwright install chromium
# or: playwright install chromium
```

### 4. (Optional) Install Upscayl for image enhancement

Download and install from: https://github.com/upscayl/upscayl/releases

The tool will automatically detect Upscayl if installed in the default location:
- Windows: `C:\Program Files\Upscayl\`

## Usage

### Generate a single guide

```bash
uv run python -m src.cli generate --url "<TUTORIAL_URL>" --output ./output
```

**Example:**
```bash
uv run python -m src.cli generate \
  --url "https://wiki.elecfreaks.com/en/microbit/building-blocks/nezha-inventors-kit/Nezha_Inventor_s_kit_for_microbit_case_01" \
  --output ./guides
```

This will create:
```
guides/
├── nezha-inventor-s-kit-for-microbit-case-01.md   # Dutch guide
└── images/                                         # Downloaded images
    ├── image_000.png
    ├── image_001.png
    └── ...
```

### Command options

| Option | Description |
|--------|-------------|
| `--url TEXT` | Tutorial page URL (required) |
| `-o, --output TEXT` | Output directory (default: `./output`) |
| `-v, --verbose` | Enable verbose/debug output |
| `--no-enhance` | Skip image enhancement (faster, smaller files) |
| `--no-translate` | Keep original English text |

### Examples

**Quick generation (no enhancement, no translation):**
```bash
uv run python -m src.cli generate \
  --url "<URL>" \
  --output ./output \
  --no-enhance \
  --no-translate
```

**Full pipeline with verbose output:**
```bash
uv run python -m src.cli generate \
  --url "<URL>" \
  --output ./output \
  -v
```

### List supported sources

```bash
uv run python -m src.cli sources
```

Currently supported:
- **wiki.elecfreaks.com** - Elecfreaks Wiki (Nezha Inventor's Kit tutorials)

## Configuration

Configuration is managed via environment variables or `.env.app` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `OUTPUT_DIR` | `./output` | Default output directory |
| `CACHE_DIR` | `./cache` | Cache for downloaded pages |
| `RATE_LIMIT_SECONDS` | `2` | Delay between requests |
| `IMAGE_DOWNLOAD_TIMEOUT` | `30` | Image download timeout (seconds) |
| `UPSCAYL_PATH` | Auto-detected | Path to Upscayl binary |
| `UPSCAYL_SCALE` | `4` | Upscale factor (2 or 4) |
| `ENHANCE_IMAGES` | `true` | Enable image enhancement |
| `TRANSLATE_ENABLED` | `true` | Enable Dutch translation |

## Project Structure

```
src/
├── cli.py              # Command-line interface
├── scraper.py          # Playwright-based page fetcher
├── extractor.py        # Content extraction orchestrator
├── downloader.py       # Async image downloader
├── enhancer.py         # Upscayl image enhancement
├── translator.py       # Dutch translation
├── generator.py        # Markdown generation
├── core/
│   ├── config.py       # Settings management
│   ├── errors.py       # Custom exceptions
│   └── logging.py      # Logging setup
└── sources/
    ├── base.py         # Base source adapter
    └── elecfreaks.py   # Elecfreaks-specific extraction
```

## Development

### Run tests

```bash
uv run pytest
```

### Run linting

```bash
uv run ruff check src/
uv run ruff format src/
```

### Install dev dependencies

```bash
uv sync --all-extras
```

## Pipeline Flow

```
URL → Fetch Page → Extract Content → Download Images → Enhance Images → Translate → Generate Markdown → Save
      (Playwright)  (BeautifulSoup)    (httpx)          (Upscayl)       (Google)    (markdownify)
```

Each stage handles errors gracefully:
- **Critical failures** (fetch, extract, generate): Stop with error message
- **Non-critical failures** (download, enhance, translate): Log warning, continue with fallback

## Troubleshooting

### "No adapter available for URL"

The URL is not from a supported source. Run `sources` command to see supported websites.

### Image enhancement fails

- Ensure Upscayl is installed
- Check that `UPSCAYL_PATH` points to the correct binary
- Use `--no-enhance` to skip enhancement

### Translation fails

- Check internet connection (requires Google Translate API)
- Use `--no-translate` to skip translation and keep English

### Browser errors

```bash
# Reinstall Playwright browsers
uv run playwright install chromium
```

## License

MIT

## Contributing

1. Fork the repository
2. Create a feature branch
3. Run tests: `uv run pytest`
4. Run linting: `uv run ruff check src/`
5. Submit a pull request
