"""MakeCode screenshot capture for Dutch code block images."""

import asyncio
import inspect
import logging
import sys
from pathlib import Path

# Add project root to path for standalone execution
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

from playwright.async_api import Browser, Page, async_playwright
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from src.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


async def capture_makecode_screenshot(
    url: str,
    output_path: Path,
    browser: Browser,
    language: str = "nl",
    timeout: int = 50000,
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
        # Create new page with larger viewport
        page = await browser.new_page(
            viewport={"width": 1920, "height": 1080}
        )
        logger.debug("    -> Created new page with 1920x1080 viewport")

        # Set language cookie to ensure Dutch language (try multiple possible cookie names)
        cookies_to_set = [
            {'name': 'PXT_LANG', 'value': language, 'domain': '.makecode.microbit.org', 'path': '/'},  # This is the key one!
            {'name': 'lang', 'value': language, 'domain': '.makecode.microbit.org', 'path': '/'},
            {'name': 'locale', 'value': language, 'domain': '.makecode.microbit.org', 'path': '/'},
            {'name': 'preferred-language', 'value': language, 'domain': '.makecode.microbit.org', 'path': '/'},
            {'name': 'makecode-lang', 'value': language, 'domain': '.makecode.microbit.org', 'path': '/'},
        ]

        for cookie in cookies_to_set:
            await page.context.add_cookies([cookie])

        logger.debug(f"    -> Set {len(cookies_to_set)} language cookies for: {language}")

        # Also set user agent to include language preference
        await page.set_extra_http_headers({
            'Accept-Language': f'{language},en;q=0.9,en;q=0.8'
        })
        logger.debug(f"    -> Set Accept-Language header: {language}")

        # Add language parameter to URL
        if "?" in url:
            # Check if lang parameter already exists
            if "lang=" in url:
                url_with_lang = url  # Use existing lang parameter
            else:
                url_with_lang = f"{url}&lang={language}"
        else:
            url_with_lang = f"{url}?lang={language}"

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

        # Wait for page to be fully loaded first
        await page.wait_for_load_state("networkidle", timeout=timeout)
        logger.debug("    -> Page network idle")

        # Try to find target element quickly (short timeout)
        editor_selectors = [
            "div.injectionDiv.pxt-renderer.classic-theme.blocklyReadOnly",
            "#maineditor",
            ".monaco-editor",
            ".blocklyDiv",
            "#blocksEditor",
        ]

        editor_element = None
        try:
            # Quick attempt to find target element (shorter timeout)
            for selector in editor_selectors:
                try:
                    editor_element = await page.wait_for_selector(selector, timeout=5000, state="visible")
                    logger.debug(f"    -> Found editor element (selector: {selector})")
                    break
                except PlaywrightTimeoutError:
                    continue
        except Exception as e:
            logger.debug(f"    -> Quick element search failed: {e}")

        # If target element not found quickly, take full page screenshot immediately
        if not editor_element:
            logger.warning("    -> Target element not found quickly, taking full page screenshot")

            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Take full page screenshot immediately
            await page.screenshot(path=str(output_path), full_page=True)
            logger.debug(f"    -> Full page screenshot saved: {output_path}")
            return True

        # If we found the element, continue with normal flow
        logger.debug("    -> Target element found, proceeding with element screenshot")

        # Wait a bit more for blocks to render and language to apply
        await asyncio.sleep(3)
        logger.debug("    -> Waited for blocks to render and language to apply")

        # Debug: Check current URL and page title
        current_url = page.url
        page_title = await page.title()
        logger.debug(f"    -> Current URL: {current_url}")
        logger.debug(f"    -> Page title: {page_title}")

        # Try to force language switch by clicking language selector if present
        try:
            # Look for language selector or dropdown
            lang_selectors = [
                '[data-test="language-selector"]',
                '.language-selector',
                '#lang-selector',
                'select[title*="language"]',
                'select[title*="taal"]',
                'button[title*="language"]',
                'button[title*="taal"]',
            ]

            for selector in lang_selectors:
                lang_element = await page.query_selector(selector)
                if lang_element:
                    logger.debug(f"    -> Found language selector: {selector}")
                    # Try to click it and then click Dutch option
                    await lang_element.click()
                    await asyncio.sleep(1)

                    # Look for Dutch option
                    dutch_selectors = [
                        'option[value="nl"]',
                        'option:has-text("Nederlands")',
                        'option:has-text("Dutch")',
                        'button:has-text("Nederlands")',
                        'button:has-text("Dutch")',
                    ]

                    for dutch_selector in dutch_selectors:
                        dutch_option = await page.query_selector(dutch_selector)
                        if dutch_option:
                            await dutch_option.click()
                            logger.debug(f"    -> Clicked Dutch option: {dutch_selector}")
                            await asyncio.sleep(2)  # Wait for language to switch
                            break
                    break
        except Exception as lang_error:
            logger.debug(f"    -> Language selector not found or error: {lang_error}")

        # Check page content for language indicators
        try:
            # Look for Dutch text on the page
            dutch_indicators = await page.evaluate("""
                () => {
                    const text = document.body.innerText.toLowerCase();
                    return {
                        hasDutch: text.includes('code bewerken') || text.includes('blokken') || text.includes('simulator'),
                        hasEnglish: text.includes('edit code') || text.includes('blocks') || text.includes('simulator'),
                        bodyText: document.body.innerText.substring(0, 200)
                    };
                }
            """)

            logger.debug(f"    -> Language check - Dutch: {dutch_indicators['hasDutch']}, English: {dutch_indicators['hasEnglish']}")
            logger.debug(f"    -> Page text sample: {dutch_indicators['bodyText']}")
        except Exception as check_error:
            logger.debug(f"    -> Could not check page language: {check_error}")

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Take screenshot
        # Try to screenshot just the editor area first
        try:
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


if __name__ == "__main__":
    async def test_capture():
        """Test the MakeCode screenshot capture functionality."""
        # Default test URL - a simple MakeCode project
        test_url = "https://makecode.microbit.org/99662-62928-32447-74027"  # Example URL

        # Default output directory
        output_dir = Path("D:/Coderdojo/test_output")
        output_dir.mkdir(exist_ok=True)

        print("Testing MakeCode screenshot capture...")
        print(f"URL: {test_url}")
        print(f"Output directory: {output_dir}")

        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=False)  # Show browser for testing

            try:
                # Test single screenshot
                output_path = output_dir / "test_makecode.png"
                success = await capture_makecode_screenshot(
                    url=test_url,
                    output_path=output_path,
                    browser=browser,
                    language="nl",
                    timeout=30000
                )

                if success:
                    print(f"✅ Screenshot saved to: {output_path}")
                else:
                    print("❌ Failed to capture screenshot")

                '''
                # Test multiple screenshots
                print("\nTesting multiple screenshots...")
                url_mapping = {
                    1: test_url,
                    2: "https://makecode.microbit.org/_xyz789uvw012"  # Another example
                }

                try:
                    results = await capture_multiple_screenshots(
                        url_mapping=url_mapping,
                        output_dir=output_dir,
                        browser=browser,
                        language="nl"
                    )

                    print(f"✅ Captured {len(results)} screenshots:")
                    for idx, path in results.items():
                        print(f"  - Image {idx}: {path}")
                except Exception as capture_error:
                    print(f"❌ Error during multiple screenshot capture: {capture_error}")
                    # Continue to browser cleanup even if capture fails
                '''
            except Exception as e:
                print(f"❌ Error during testing: {e}")

            finally:
                await browser.close()
                print("🔚 Browser closed")

    # Run the test
    asyncio.run(test_capture())
