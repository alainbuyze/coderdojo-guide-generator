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
        "coding",
        "programma",  # Dutch for program
    ]

    # Section headings that indicate code content
    CODE_SECTION_HEADINGS = [
        "code",
        "program",
        "makecode",
        "coding",
        "codeer",  # Dutch for code
        "programmeer",  # Dutch for program
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

    def _is_code_section(self, heading: str) -> bool:
        """Check if a section heading indicates code content.

        Args:
            heading: Section heading text.

        Returns:
            True if the heading suggests code content.
        """
        heading_lower = heading.lower()
        return any(keyword in heading_lower for keyword in self.CODE_SECTION_HEADINGS)

    def find_code_images_in_sections(
        self, sections: list[dict[str, Any]], all_images: list[dict[str, str]]
    ) -> list[int]:
        """Find image indices that appear in code-related sections.

        Args:
            sections: List of section dicts with heading and content.
            all_images: List of all image dicts.

        Returns:
            List of image indices that are in code sections.
        """
        code_image_indices = []

        # Build a set of image srcs for quick lookup
        image_src_to_idx = {img.get("src", ""): idx for idx, img in enumerate(all_images)}

        for section in sections:
            heading = section.get("heading", "")
            if not self._is_code_section(heading):
                continue

            # Find images in this section's content
            content = section.get("content", [])
            for element in content:
                element_str = str(element)
                # Look for img tags
                for src, idx in image_src_to_idx.items():
                    if src and src in element_str:
                        if idx not in code_image_indices:
                            code_image_indices.append(idx)
                            logger.debug(f"Found code image {idx} in section '{heading}'")

        return code_image_indices

    def match_images_to_links(
        self, images: list[dict[str, str]], links: list[str], sections: list[dict[str, Any]] | None = None
    ) -> dict[int, str]:
        """Match code screenshots to their MakeCode project URLs.

        Uses heuristics to pair images with links:
        1. Images in code-related sections (by heading)
        2. Images with code keywords in alt/title/src
        3. Multiple code images map to multiple links in order

        Args:
            images: List of image dicts with src, alt, title.
            links: List of MakeCode project URLs.
            sections: Optional list of sections for context-based detection.

        Returns:
            Dictionary mapping image index to MakeCode URL.
        """
        logger.debug(f"Matching {len(images)} images to {len(links)} MakeCode links")

        if not links:
            logger.debug("No MakeCode links to match")
            return {}

        # Find code images by keyword matching
        keyword_code_images = [
            idx for idx, img in enumerate(images) if self._is_code_image(img, idx)
        ]

        # Find code images by section context
        section_code_images = []
        if sections:
            section_code_images = self.find_code_images_in_sections(sections, images)

        # Combine and deduplicate, preserving order
        all_code_indices = []
        for idx in keyword_code_images + section_code_images:
            if idx not in all_code_indices:
                all_code_indices.append(idx)

        # Sort by index to maintain image order
        all_code_indices.sort()

        if not all_code_indices:
            logger.debug("No code images detected")
            return {}

        logger.debug(f"Found {len(all_code_indices)} code images (keywords: {len(keyword_code_images)}, sections: {len(section_code_images)})")

        # Match images to links in order
        matches = {}
        for i, img_idx in enumerate(all_code_indices):
            if i < len(links):
                matches[img_idx] = links[i]
                logger.debug(f"Matched image {img_idx} to link {links[i]}")

        if len(links) > len(all_code_indices):
            logger.warning(
                f"Found {len(links)} MakeCode links but only {len(all_code_indices)} code images"
            )

        return matches
