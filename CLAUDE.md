# CoderDojo Guide Generator

A tool to create printable Dutch instruction guides from online maker kit tutorials.

## Tech Stack

- **Language:** Python 3.11+
- **Browser Automation:** Playwright
- **HTML Parsing:** BeautifulSoup4
- **Translation:** deep-translator
- **Image Enhancement:** Upscayl (external tool)
- **CLI:** Click
- **Progress/UI:** Rich
Review default standards in @C:\Users\alain\CascadeProjects\Coderdojo\guides

## Project Structure

```
src/
├── cli.py                  # Command-line interface
├── pipeline.py             # Orchestrates the full workflow
├── scraper.py              # Playwright-based page fetcher
├── extractor.py            # BeautifulSoup content extraction
├── makecode_detector.py    # Detects MakeCode links and code images
├── makecode_capture.py     # Captures Dutch MakeCode screenshots
├── makecode_replacer.py    # Replaces English screenshots with Dutch
├── downloader.py           # Downloads images
├── enhancer.py             # Upscayl image processing
├── translator.py           # Dutch translation
├── generator.py            # Markdown generation
└── sources/
    ├── base.py             # Base source adapter
    └── elecfreaks.py       # Elecfreaks-specific extraction rules
tests/                      # Test files
output/                     # Generated guides (gitignored)
cache/                      # Downloaded pages cache (gitignored)
```

## Common Commands

**Setup:**

**Windows (PowerShell):**
```powershell
uv sync                           # Install dependencies
playwright install chromium       # Install browser for scraping
```

**Windows (Command Prompt):**
```cmd
uv sync                           # Install dependencies
playwright install chromium       # Install browser for scraping
```

**Linux/macOS:**
```bash
uv sync                           # Install dependencies
playwright install chromium       # Install browser for scraping
```

**Run:**

**Windows (PowerShell):**
```powershell
# Generate single guide
uv run python -m src.cli generate --url "<URL>" --output ./output

# Generate guide without MakeCode replacement
uv run python -m src.cli generate --url "<URL>" --output ./output --no-makecode

# Generate all guides from index
uv run python -m src.cli batch --index "<URL>" --output ./output

# List tutorials without processing
uv run python -m src.cli batch --index "<URL>" --list-only
```

**Windows (Command Prompt):**
```cmd
# Generate single guide
uv run python -m src.cli generate --url "<URL>" --output ./output

# Generate guide without MakeCode replacement
uv run python -m src.cli generate --url "<URL>" --output ./output --no-makecode

# Generate all guides from index
uv run python -m src.cli batch --index "<URL>" --output ./output

# List tutorials without processing
uv run python -m src.cli batch --index "<URL>" --list-only
```

**Linux/macOS:**
```bash
# Generate single guide
uv run python -m src.cli generate --url "<URL>" --output ./output

# Generate guide without MakeCode replacement
uv run python -m src.cli generate --url "<URL>" --output ./output --no-makecode

# Generate all guides from index
uv run python -m src.cli batch --index "<URL>" --output ./output

# List tutorials without processing
uv run python -m src.cli batch --index "<URL>" --list-only
```

**Test:**

**Windows:**
```powershell
uv run pytest
```

**Linux/macOS:**
```bash
uv run pytest
```

**Lint:**

**Windows:**
```powershell
uv run ruff check src/
uv run ruff format src/
```

**Linux/macOS:**
```bash
uv run ruff check src/
uv run ruff format src/
```

## Configuration

Key paths and settings (configurable via environment variables):
- **Upscayl:** `UPSCAYL_PATH=C:/Program Files/Upscayl/resources/bin/upscayl-bin.exe` (Windows default)
- **Output:** `OUTPUT_DIR=./output`
- **Cache:** `CACHE_DIR=./cache`
- **MakeCode Language:** `MAKECODE_LANGUAGE=nl` (default: Dutch)
- **MakeCode Timeout:** `MAKECODE_TIMEOUT=30000` (ms, default: 30s)
- **MakeCode Replacement:** `MAKECODE_REPLACE_ENABLED=True` (default: enabled)

### Windows-Specific Settings

**Environment Variables (.env.app):**
```env
# Use forward slashes in .env files - Python handles conversion
UPSCAYL_PATH=C:/Program Files/Upscayl/resources/bin/upscayl-bin.exe
OUTPUT_DIR=./output
CACHE_DIR=./cache
IMAGE_OUTPUT_DIR=images
```

**Path Handling in Code:**
```python
from pathlib import Path
from src.core.config import get_settings

settings = get_settings()

# ✅ GOOD - Cross-platform compatible
upscayl_path = Path(settings.UPSCAYL_PATH)
output_dir = settings.output_path  # Path property from config
image_dir = output_dir / settings.IMAGE_OUTPUT_DIR

# ❌ BAD - Windows-specific
upscayl_path = "C:\\Program Files\\Upscayl\\upscayl.exe"
output_dir = settings.OUTPUT_DIR + "\\images"
```

## Code Conventions

- Use type hints for all function signatures
- Use Pydantic for configuration and data validation
- Each source site has its own adapter in `src/sources/`
- Use `rich` for all console output (progress bars, tables, etc.)
- Keep functions focused and testable

### Windows Compatibility Requirements

**Path Operations:**
- **Always** use `pathlib.Path` for file operations
- **Never** hard-code backslashes in Python code
- **Use** `Path.resolve()` for subprocess commands to avoid working directory issues
- **Convert** Path objects to strings when passing to external tools

**Subprocess Commands:**
- **Build** commands as lists, not strings (avoids shell injection issues)
- **Use** `subprocess.run()` with `text=True` for proper encoding handling
- **Set** `cwd` parameter for external tools that need specific working directories
- **Handle** timeouts and encoding errors gracefully

**Example - Upscayl Integration:**
```python
import subprocess
from pathlib import Path
from src.core.config import get_settings

def enhance_image(input_path: Path, output_path: Path) -> bool:
    """Enhance image using Upscayl with Windows compatibility."""
    settings = get_settings()
    upscayl_bin = Path(settings.UPSCAYL_PATH)
    
    if not upscayl_bin.exists():
        logger.error(f"Upscayl not found at: {upscayl_bin}")
        return False
    
    # Use absolute paths
    input_abs = input_path.resolve()
    output_abs = output_path.resolve()
    
    # Build command as list
    cmd = [
        str(upscayl_bin),
        "-i", str(input_abs),
        "-o", str(output_abs),
        "-n", settings.UPSCAYL_MODEL,
        "-z", str(settings.UPSCAYL_SCALE)
    ]
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(upscayl_bin.parent.parent),  # resources directory
            capture_output=True,
            text=True,
            timeout=120
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        logger.warning(f"Enhancement timed out: {input_path}")
        return False
```

# Environment Instructions

This is a Windows environment using PowerShell/CMD, NOT bash.

## Shell Commands
- Use PowerShell commands, not bash/Unix commands
- Use `Get-Content` instead of `cat`
- Use `type` (CMD) or `Get-Content` (PowerShell) for reading files
- Use Windows paths with backslashes: `C:\Users\alain\...`
- Do NOT use Unix paths like `/c/Users/...`

## File Operations
- Reading files: `Get-Content "C:\path\to\file"`
- Listing directories: `Get-ChildItem` or `dir`
- Current directory: `Get-Location` or `pwd`

## Development Workflow

1. Use `/project:core_piv_loop:prime` to load project context
2. Use `/project:core_piv_loop:plan-feature` to plan new features
3. Use `/project:core_piv_loop:execute` to implement plans
4. Use `/project:validation:validate` to verify changes
5. Use `/project:commit` to commit changes

## Important Context

- Target site: Elecfreaks Wiki (wiki.elecfreaks.com)
- Images hosted on Aliyun CDN
- 76 tutorials in Nezha Inventor's Kit
- Upscayl has limited CLI support - may need workarounds
- Rate limiting important to avoid IP blocking
- MakeCode screenshots: Automatically replaces English code block images with Dutch versions
  - Detects MakeCode links in "Reference" sections
  - Matches code images to MakeCode project URLs
  - Captures Dutch screenshots using Playwright
  - Gracefully falls back to original images on failure

## External Resources

- [PRD.md](./PRD.md) - Full product requirements
- [Elecfreaks Wiki](https://wiki.elecfreaks.com/en/microbit/building-blocks/nezha-inventors-kit/)
- [Upscayl](https://github.com/upscayl/upscayl)
- [Playwright Python](https://playwright.dev/python/)
