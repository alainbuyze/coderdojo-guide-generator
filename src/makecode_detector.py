"""MakeCode image detector - finds image/link pairs from HTML structure."""

import logging
import re
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

# Pattern for MakeCode project URLs
MAKECODE_URL_PATTERN = re.compile(
    r"https?://makecode\.microbit\.org/_[A-Za-z0-9]+",
    re.IGNORECASE,
)


def find_makecode_image_pairs(html: str | Tag) -> dict[str, str]:
    """Find image URLs paired with their MakeCode project links.

    Looks for the pattern where a paragraph with an image is immediately
    followed by a paragraph containing a MakeCode link:

        <p><img src="..."></p>
        <p>Link: <a href="https://makecode.microbit.org/_xxx">...</a></p>

    Args:
        html: HTML string or BeautifulSoup Tag to search.

    Returns:
        Dictionary mapping image src URLs to MakeCode project URLs.
    """
    if isinstance(html, str):
        soup = BeautifulSoup(html, "html.parser")
    else:
        soup = html

    pairs: dict[str, str] = {}

    # Find all <a> tags with MakeCode URLs
    for link in soup.find_all("a", href=MAKECODE_URL_PATTERN):
        makecode_url = link.get("href", "")
        if not makecode_url:
            continue

        # Find the parent <p> of this link
        link_paragraph = link.find_parent("p")
        if not link_paragraph:
            continue

        # Look back up to 3 paragraphs for the image
        img_src = None
        prev_sibling = link_paragraph.find_previous_sibling()
        for _ in range(3):
            if not prev_sibling:
                break
            if prev_sibling.name == "p":
                img = prev_sibling.find("img")
                if img:
                    img_src = img.get("src", "")
                    break
            prev_sibling = prev_sibling.find_previous_sibling()

        if not img_src:
            continue

        pairs[img_src] = makecode_url
        logger.debug(f"Found pair: {img_src} -> {makecode_url}")

    if len(pairs) == 0:
        logger.warning("No MakeCode image pairs found")
    else:
        logger.debug(f"Found {len(pairs)} MakeCode image pairs")

    return pairs


if __name__ == "__main__":
    """Test with sample HTML."""
    logging.basicConfig(level=logging.DEBUG)

    test_html = """
    <div>
        <p><img src="https://example.com/image1.png"></p>
        <p>Link: <a href="https://makecode.microbit.org/_abc123">https://makecode.microbit.org/_abc123</a></p>

        <p>Some other text</p>

        <p><img src="https://example.com/image2.png"></p>
        <p>Link: <a href="https://makecode.microbit.org/_xyz789">https://makecode.microbit.org/_xyz789</a></p>
    </div>
    """

    pairs = find_makecode_image_pairs(test_html)
    print(f"Found pairs: {pairs}")
