"""MakeCode image detector for identifying code screenshots and project links."""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class MakeCodeImageDetector:
    """Detects MakeCode code screenshots and associated project links."""

    # Pattern for MakeCode project URLs
    MAKECODE_URL_PATTERN = re.compile(
        r"https?://makecode\.microbit\.org/_[A-Za-z0-9]+",
        re.IGNORECASE,
    )

    # Keywords that suggest an image is a code screenshot
    CODE_IMAGE_KEYWORDS = [
        "code",
        "program",
        "makecode",
        "scratch",
        "blocks",
        "script",
    ]

    def find_makecode_links(self, sections: list[dict[str, Any]]) -> list[str]:
        """Extract MakeCode project URLs from content sections.

        Args:
            sections: List of section dicts with heading and content.

        Returns:
            List of MakeCode project URLs found in the content.
        """
        logger.debug(f"Searching for MakeCode links in {len(sections)} sections")
        links = []

        for section in sections:
            # Check section heading
            heading = section.get("heading", "")
            found_in_heading = self.MAKECODE_URL_PATTERN.findall(heading)
            links.extend(found_in_heading)

            # Check section content (BeautifulSoup Tag objects)
            content = section.get("content", [])
            for element in content:
                # Convert element to string to search for URLs
                element_str = str(element)
                found_in_content = self.MAKECODE_URL_PATTERN.findall(element_str)
                links.extend(found_in_content)

        # Remove duplicates while preserving order
        unique_links = list(dict.fromkeys(links))
        logger.debug(f"Found {len(unique_links)} unique MakeCode links")
        return unique_links

    def _is_code_image(self, image: dict[str, str], index: int) -> bool:
        """Check if an image is likely a code screenshot.

        Args:
            image: Image dict with src, alt, title.
            index: Image index in the list.

        Returns:
            True if the image appears to be a code screenshot.
        """
        # Check alt text and title for code-related keywords
        alt = image.get("alt", "").lower()
        title = image.get("title", "").lower()
        src = image.get("src", "").lower()

        text_to_check = f"{alt} {title} {src}"

        for keyword in self.CODE_IMAGE_KEYWORDS:
            if keyword in text_to_check:
                logger.debug(f"Image {index} matched keyword '{keyword}': {alt or title or src}")
                return True

        return False

    def match_images_to_links(
        self, images: list[dict[str, str]], links: list[str]
    ) -> dict[int, str]:
        """Match code screenshots to their MakeCode project URLs.

        Uses heuristics to pair images with links:
        1. Code images typically appear before reference links
        2. Multiple code images map to multiple links in order
        3. Only images matching code keywords are considered

        Args:
            images: List of image dicts with src, alt, title.
            links: List of MakeCode project URLs.

        Returns:
            Dictionary mapping image index to MakeCode URL.
        """
        logger.debug(f"Matching {len(images)} images to {len(links)} MakeCode links")

        if not links:
            logger.debug("No MakeCode links to match")
            return {}

        # Find all code images
        code_images = [
            (idx, img) for idx, img in enumerate(images) if self._is_code_image(img, idx)
        ]

        if not code_images:
            logger.debug("No code images detected")
            return {}

        logger.debug(f"Found {len(code_images)} code images")

        # Match images to links in order
        matches = {}
        for i, (img_idx, _) in enumerate(code_images):
            if i < len(links):
                matches[img_idx] = links[i]
                logger.debug(f"Matched image {img_idx} to link {links[i]}")
            else:
                # More code images than links - log warning
                logger.warning(f"Code image at index {img_idx} has no corresponding MakeCode link")

        if len(links) > len(code_images):
            logger.warning(
                f"Found {len(links)} MakeCode links but only {len(code_images)} code images"
            )

        return matches
