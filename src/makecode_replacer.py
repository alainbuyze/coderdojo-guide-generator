"""MakeCode screenshot replacement logic."""

import inspect
import logging
from pathlib import Path

from playwright.async_api import Browser

from src.core.config import get_settings
from src.makecode_capture import capture_multiple_screenshots
from src.makecode_detector import MakeCodeImageDetector
from src.sources.base import ExtractedContent

settings = get_settings()
logger = logging.getLogger(__name__)


async def replace_makecode_screenshots(
    content: ExtractedContent,
    output_dir: Path,
    browser: Browser,
    language: str = "nl",
) -> ExtractedContent:
    """Replace English MakeCode screenshots with Dutch versions.

    Args:
        content: Extracted content with images.
        output_dir: Base output directory.
        browser: Playwright browser instance.
        language: Target language for screenshots (default: 'nl').

    Returns:
        Updated ExtractedContent with Dutch screenshots.
    """
    logger.debug(f" * {inspect.currentframe().f_code.co_name} > Processing MakeCode replacements")

    # Step 1: Detect MakeCode links and code images
    detector = MakeCodeImageDetector()

    makecode_links = detector.find_makecode_links(content.sections)
    if not makecode_links:
        logger.debug("    -> No MakeCode links found, skipping replacement")
        return content

    logger.debug(f"    -> Found {len(makecode_links)} MakeCode links")

    # Step 2: Match images to links
    image_to_link_map = detector.match_images_to_links(content.images, makecode_links)
    if not image_to_link_map:
        logger.debug("    -> No code images matched to links, skipping replacement")
        return content

    logger.debug(f"    -> Matched {len(image_to_link_map)} images to MakeCode links")

    # Step 3: Capture Dutch screenshots
    images_dir = output_dir / settings.IMAGE_OUTPUT_DIR
    images_dir.mkdir(parents=True, exist_ok=True)

    captured_screenshots = await capture_multiple_screenshots(
        image_to_link_map, images_dir, browser, language
    )

    if not captured_screenshots:
        logger.warning("    -> No screenshots captured successfully")
        return content

    logger.debug(f"    -> Captured {len(captured_screenshots)} Dutch screenshots")

    # Step 4: Update image references
    replaced_count = 0
    for img_idx, screenshot_path in captured_screenshots.items():
        if img_idx < len(content.images):
            # Store original for potential backup/debugging
            original_src = content.images[img_idx].get("src")
            logger.debug(f"    -> Replacing image {img_idx}: {original_src}")

            # Update image dict with Dutch screenshot
            relative_path = str(Path(settings.IMAGE_OUTPUT_DIR) / screenshot_path.name)
            content.images[img_idx]["local_path"] = relative_path
            content.images[img_idx]["makecode_url"] = image_to_link_map[img_idx]
            content.images[img_idx]["replaced_with_dutch"] = True

            # Keep original URL for reference
            if "src" not in content.images[img_idx].get("_original", {}):
                content.images[img_idx]["_original_src"] = original_src

            replaced_count += 1

    logger.debug(f"    -> Replaced {replaced_count} images with Dutch versions")

    # Update metadata
    content.metadata["makecode_replacements"] = replaced_count
    content.metadata["makecode_links_found"] = len(makecode_links)

    return content
