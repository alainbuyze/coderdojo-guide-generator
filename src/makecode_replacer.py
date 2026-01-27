"""MakeCode screenshot replacement logic."""

import inspect
import logging
from pathlib import Path

from playwright.async_api import Browser

from src.core.config import get_settings
from src.makecode_capture import capture_multiple_screenshots
from src.makecode_detector import find_makecode_image_pairs
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

    # Find image/MakeCode URL pairs from section content
    # Aggregate all content elements first, then call detector once
    all_html_parts = []
    for section in content.sections:
        all_html_parts.extend(section.get("content", []))

    src_to_makecode: dict[str, str] = {}
    if all_html_parts:
        combined_html = "".join(str(e) for e in all_html_parts)
        src_to_makecode = find_makecode_image_pairs(combined_html)

    if not src_to_makecode:
        logger.debug("    -> No MakeCode image pairs found, skipping replacement")
        return content

    logger.debug(f"    -> Found {len(src_to_makecode)} MakeCode image pairs")

    # Build index-based mapping for capture function
    image_to_link_map: dict[int, str] = {}
    for idx, img in enumerate(content.images):
        src = img.get("src", "")
        if src in src_to_makecode:
            image_to_link_map[idx] = src_to_makecode[src]

    if not image_to_link_map:
        logger.debug("    -> No images matched to MakeCode links")
        return content

    # Capture Dutch screenshots
    images_dir = output_dir / settings.IMAGE_OUTPUT_DIR
    images_dir.mkdir(parents=True, exist_ok=True)

    captured_screenshots = await capture_multiple_screenshots(
        image_to_link_map, images_dir, browser, language
    )

    if not captured_screenshots:
        logger.warning("    -> No screenshots captured successfully")
        return content

    logger.debug(f"    -> Captured {len(captured_screenshots)} Dutch screenshots")

    # Update image references
    replaced_count = 0
    guide_name = output_dir.name
    for img_idx, screenshot_path in captured_screenshots.items():
        if img_idx < len(content.images):
            original_src = content.images[img_idx].get("src")
            logger.debug(f"    -> Replacing image {img_idx}: {original_src}")

            relative_path = str(Path(guide_name) / settings.IMAGE_OUTPUT_DIR / screenshot_path.name)
            content.images[img_idx]["local_path"] = relative_path
            content.images[img_idx]["makecode_url"] = image_to_link_map[img_idx]
            content.images[img_idx]["replaced_with_dutch"] = True
            content.images[img_idx]["_original_src"] = original_src
            replaced_count += 1

    logger.debug(f"    -> Replaced {replaced_count} images with Dutch versions")

    content.metadata["makecode_replacements"] = replaced_count
    content.metadata["makecode_pairs_found"] = len(src_to_makecode)

    return content
