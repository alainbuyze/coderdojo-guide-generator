"""Elecfreaks Wiki source adapter for content extraction."""

import inspect
import logging
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from src.core.config import get_settings
from src.sources.base import BaseSourceAdapter, ExtractedContent, TutorialLink

settings = get_settings()
logger = logging.getLogger(__name__)


class ElecfreaksAdapter(BaseSourceAdapter):
    """Adapter for extracting content from Elecfreaks Wiki pages.

    The Elecfreaks Wiki uses Docusaurus, so we look for specific
    CSS classes and structure typical of that platform.
    """

    DOMAIN_PATTERNS = [
        "wiki.elecfreaks.com",
        "elecfreaks.com/wiki",
    ]

    # CSS selectors for content removal (navigation, sidebars, etc.)
    REMOVE_SELECTORS = [
        ".navbar",
        ".sidebar",
        ".footer",
        ".breadcrumbs",
        ".toc",
        ".pagination-nav",
        ".theme-doc-sidebar-container",
        ".theme-doc-footer",
        ".theme-doc-toc-mobile",
        "nav",
        "footer",
        "[class*='breadcrumb']",
        "[class*='sidebar']",
        "[class*='pagination']",
    ]

    # CSS selectors for main content (in priority order)
    CONTENT_SELECTORS = [
        ".theme-doc-markdown.markdown",  # Most specific for Docusaurus
        ".theme-doc-markdown",
        "article .markdown",
        ".markdown",
        "article",
        "main",
        ".docMainContainer",
    ]

    def can_handle(self, url: str) -> bool:
        """Check if this adapter can handle the given URL.

        Args:
            url: The URL to check.

        Returns:
            True if URL is from Elecfreaks Wiki.
        """
        return any(pattern in url.lower() for pattern in self.DOMAIN_PATTERNS)

    def extract(self, soup: BeautifulSoup, url: str) -> ExtractedContent:
        """Extract content from an Elecfreaks Wiki page.

        Args:
            soup: Parsed HTML as BeautifulSoup object.
            url: The source URL for context.

        Returns:
            ExtractedContent with title, sections, images, and metadata.
        """
        logger.debug(f" * {inspect.currentframe().f_code.co_name} > Extracting from: {url}")

        # Remove unwanted elements
        self._remove_navigation(soup)

        # Find main content
        main_content = self._find_main_content(soup)
        if main_content is None:
            logger.warning("    -> Could not find main content, using body")
            main_content = soup.body or soup

        # Extract title
        title = self._extract_title(main_content, soup)
        logger.debug(f"    -> Title: {title}")

        # Extract sections
        sections = self._extract_sections(main_content)
        logger.debug(f"    -> Found {len(sections)} sections")

        # Extract images
        images = self._extract_images(main_content, url)
        logger.debug(f"    -> Found {len(images)} images")

        # Extract metadata
        metadata = self._extract_metadata(soup, url)

        return ExtractedContent(
            title=title,
            sections=sections,
            images=images,
            metadata=metadata,
        )

    def _remove_navigation(self, soup: BeautifulSoup) -> None:
        """Remove navigation and sidebar elements from the soup."""
        for selector in self.REMOVE_SELECTORS:
            for element in soup.select(selector):
                element.decompose()

    def _find_main_content(self, soup: BeautifulSoup) -> Tag | None:
        """Find the main content container."""
        for selector in self.CONTENT_SELECTORS:
            content = soup.select_one(selector)
            if content:
                logger.debug(f"    -> Found content using selector: {selector}")
                return content
        return None

    def _extract_title(self, content: Tag, soup: BeautifulSoup) -> str:
        """Extract the page title."""
        # Try h1 in content first
        h1 = content.find("h1")
        if h1 and h1.get_text(strip=True):
            return h1.get_text(strip=True)

        # Fall back to page title
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)
            # Remove site suffix
            title = re.sub(r"\s*\|\s*.*$", "", title)
            title = re.sub(r"\s*-\s*.*$", "", title)
            return title

        return "Untitled"

    def _extract_sections(self, content: Tag) -> list[dict]:
        """Extract content sections split by h2 headers."""
        sections = []
        current_section: dict = {"heading": "", "content": [], "level": 0}

        # Remove h1 from content to avoid duplication (title already extracted)
        h1 = content.find("h1")
        if h1:
            h1.decompose()

        for element in content.children:
            if not isinstance(element, Tag):
                continue

            if element.name in ("h2", "h3", "h4"):
                # Save previous section if it has content
                if current_section["content"]:
                    sections.append(current_section)

                # Start new section
                level = int(element.name[1])
                current_section = {
                    "heading": element.get_text(strip=True),
                    "content": [],
                    "level": level,
                }
            else:
                # Add to current section
                current_section["content"].append(element)

        # Don't forget the last section
        if current_section["content"]:
            sections.append(current_section)

        return sections

    def _extract_images(self, content: Tag, base_url: str) -> list[dict]:
        """Extract images from the content."""
        images = []

        for img in content.find_all("img"):
            src = img.get("src", "")
            if not src:
                continue

            # Make URL absolute
            if src.startswith("//"):
                src = "https:" + src
            elif not src.startswith(("http://", "https://")):
                src = urljoin(base_url, src)

            alt = img.get("alt", "")
            title = img.get("title", "")

            images.append(
                {
                    "src": src,
                    "alt": alt,
                    "title": title,
                }
            )

        return images

    def _extract_metadata(self, soup: BeautifulSoup, url: str) -> dict:
        """Extract page metadata."""
        metadata = {"url": url, "source": "elecfreaks"}

        # Try to extract description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            metadata["description"] = meta_desc["content"]

        return metadata

    def extract_tutorial_links(self, soup: BeautifulSoup, url: str) -> list[TutorialLink]:
        """Extract tutorial links from an Elecfreaks index page.

        Extracts case tutorial links from the navigation sidebar. Links
        are identified by containing "case" in the URL path.

        Args:
            soup: Parsed HTML as BeautifulSoup object.
            url: The source URL for context.

        Returns:
            List of TutorialLink objects with url and title.
        """
        logger.debug(f" * {inspect.currentframe().f_code.co_name} > Extracting tutorial links from: {url}")

        tutorials: list[TutorialLink] = []
        seen_urls: set[str] = set()

        # Find all links in the page
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            text = link.get_text(strip=True)

            # Skip empty links
            if not href or not text:
                continue

            # Look for case tutorial links
            # Pattern: URLs containing "case" in the path
            if "case" not in href.lower():
                continue

            # Make URL absolute
            if href.startswith("/"):
                href = urljoin(url, href)
            elif not href.startswith(("http://", "https://")):
                href = urljoin(url, href)

            # Skip if we've already seen this URL
            if href in seen_urls:
                continue
            seen_urls.add(href)

            # Skip the current page
            if href.rstrip("/") == url.rstrip("/"):
                continue

            # Extract and clean up the title
            title = text.strip()

            tutorials.append(TutorialLink(url=href, title=title))
            logger.debug(f"    -> Found tutorial: {title}")

        logger.info(f"    -> Found {len(tutorials)} tutorials")
        return tutorials
