"""MakeCode screenshot capture for Dutch code block images."""

import asyncio
import inspect
import logging
from pathlib import Path

from playwright.async_api import Browser, Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from src.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


async def capture_makecode_screenshot(
    url: str,
    output_path: Path,
    browser: Browser,
    language: str = "nl",
    timeout: int = 30000,
) -> bool:
    """Capture a screenshot of MakeCode editor in specified language.

    Args:
        url: MakeCode project URL (e.g., https://makecode.microbit.org/_iscUF8CzzYMd)
        output_path: Where to save the screenshot.
        browser: Playwright browser instance (reused from scraper).
        language: Language code (default: 'nl' for Dutch).
        timeout: Timeout in milliseconds for page load.

    Returns:
        True if screenshot captured successfully, False otherwise.
    """
    logger.debug(f" * {inspect.currentframe().f_code.co_name} > Capturing: {url}")

    page: Page | None = None

    try:
        # Create new page
        page = await browser.new_page()
        logger.debug("    -> Created new page")

        # Add language parameter to URL
        url_with_lang = f"{url}?lang={language}" if "?" not in url else f"{url}&lang={language}"
        logger.debug(f"    -> Loading URL with language: {url_with_lang}")

        # Navigate to URL
        response = await page.goto(url_with_lang, timeout=timeout)

        if response is None:
            logger.error("    -> No response received")
            return False

        if response.status >= 400:
            logger.error(f"    -> HTTP {response.status}")
            return False

        # Wait for editor to load
        logger.debug("    -> Waiting for editor to load")

        # Try multiple selectors for the editor
        editor_selectors = [
            "#maineditor",
            ".monaco-editor",
            ".blocklyDiv",
            "#blocksEditor",
        ]

        editor_loaded = False
        for selector in editor_selectors:
            try:
                await page.wait_for_selector(selector, timeout=timeout, state="visible")
                logger.debug(f"    -> Editor loaded (selector: {selector})")
                editor_loaded = True
                break
            except PlaywrightTimeoutError:
                continue

        if not editor_loaded:
            logger.warning("    -> Editor did not load within timeout")
            # Continue anyway, might still get a useful screenshot

        # Wait a bit more for blocks to render
        await asyncio.sleep(2)
        logger.debug("    -> Waited for blocks to render")

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Take screenshot
        # Try to screenshot just the editor area first
        try:
            editor_element = await page.query_selector("#maineditor")
            if editor_element:
                await editor_element.screenshot(path=str(output_path))
                logger.debug(f"    -> Screenshot saved (element): {output_path}")
            else:
                # Fall back to full page screenshot
                await page.screenshot(path=str(output_path), full_page=True)
                logger.debug(f"    -> Screenshot saved (full page): {output_path}")
        except Exception as screenshot_error:
            logger.warning(f"    -> Element screenshot failed: {screenshot_error}")
            # Fall back to full page screenshot
            await page.screenshot(path=str(output_path), full_page=True)
            logger.debug(f"    -> Screenshot saved (full page fallback): {output_path}")

        return True

    except PlaywrightTimeoutError as e:
        logger.error(f"    -> Timeout loading MakeCode page: {e}")
        return False

    except Exception as e:
        logger.error(f"    -> Failed to capture screenshot: {e}")
        return False

    finally:
        if page:
            await page.close()
            logger.debug("    -> Page closed")


async def capture_multiple_screenshots(
    url_mapping: dict[int, str],
    output_dir: Path,
    browser: Browser,
    language: str = "nl",
) -> dict[int, Path]:
    """Capture multiple MakeCode screenshots.

    Args:
        url_mapping: Dict mapping image index to MakeCode URL.
        output_dir: Base output directory for screenshots.
        browser: Playwright browser instance.
        language: Language code for screenshots.

    Returns:
        Dict mapping image index to saved screenshot path (only successful captures).
    """
    logger.debug(
        f" * {inspect.currentframe().f_code.co_name} > Capturing {len(url_mapping)} screenshots"
    )

    results = {}

    for img_idx, makecode_url in url_mapping.items():
        # Generate output path
        filename = f"makecode_{img_idx:03d}.png"
        output_path = output_dir / filename

        # Capture screenshot
        success = await capture_makecode_screenshot(makecode_url, output_path, browser, language)

        if success:
            results[img_idx] = output_path
            logger.debug(f"    -> Successfully captured image {img_idx}")
        else:
            logger.warning(f"    -> Failed to capture image {img_idx}")

        # Rate limiting between captures
        if settings.RATE_LIMIT_SECONDS > 0:
            await asyncio.sleep(settings.RATE_LIMIT_SECONDS)

    logger.debug(f"    -> Successfully captured {len(results)}/{len(url_mapping)} screenshots")
    return results
