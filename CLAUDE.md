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
```bash
uv sync                           # Install dependencies
playwright install chromium       # Install browser for scraping
```

**Run:**
```bash
# Generate single guide
python -m src.cli generate --url "<URL>" --output ./output

# Generate guide without MakeCode replacement
python -m src.cli generate --url "<URL>" --output ./output --no-makecode

# Generate all guides from index
python -m src.cli batch --index "<URL>" --output ./output

# List tutorials without processing
python -m src.cli batch --index "<URL>" --list-only
```

**Test:**
```bash
uv run pytest
```

**Lint:**
```bash
uv run ruff check src/
uv run ruff format src/
```

## Configuration

Key paths and settings (configurable via environment variables):
- **Upscayl:** `C:\Program Files\Upscayl\Upscayl.exe`
- **Output:** `./output`
- **Cache:** `./cache`
- **MakeCode Language:** `MAKECODE_LANGUAGE=nl` (default: Dutch)
- **MakeCode Timeout:** `MAKECODE_TIMEOUT=30000` (ms, default: 30s)
- **MakeCode Replacement:** `MAKECODE_REPLACE_ENABLED=True` (default: enabled)

## Code Conventions

- Use type hints for all function signatures
- Use Pydantic for configuration and data validation
- Each source site has its own adapter in `src/sources/`
- Use `rich` for all console output (progress bars, tables, etc.)
- Keep functions focused and testable

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
