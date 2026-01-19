"""Content extraction orchestrator using source adapters."""

import inspect
import logging

from bs4 import BeautifulSoup

from src.core.config import get_settings
from src.core.errors import ExtractionError
from src.sources.base import BaseSourceAdapter, ExtractedContent, TutorialLink
from src.sources.elecfreaks import ElecfreaksAdapter

settings = get_settings()
logger = logging.getLogger(__name__)


class ContentExtractor:
    """Orchestrates content extraction using appropriate source adapters."""

    def __init__(self) -> None:
        """Initialize with available source adapters."""
        self.adapters: list[BaseSourceAdapter] = [
            ElecfreaksAdapter(),
        ]
        logger.debug(f"    -> Initialized with {len(self.adapters)} adapters")

    def extract(self, html: str, url: str) -> ExtractedContent:
        """Extract content from HTML using the appropriate adapter.

        Args:
            html: Raw HTML content.
            url: The source URL.

        Returns:
            ExtractedContent with structured tutorial content.

        Raises:
            ExtractionError: If no adapter can handle the URL or extraction fails.
        """
        logger.debug(f" * {inspect.currentframe().f_code.co_name} > Processing URL: {url}")

        # Find matching adapter
        adapter = self._find_adapter(url)
        if adapter is None:
            raise ExtractionError(f"No adapter available for URL: {url}")

        logger.debug(f"    -> Using adapter: {type(adapter).__name__}")

        # Parse HTML
        soup = BeautifulSoup(html, "html.parser")
        logger.debug(f"    -> Parsed HTML ({len(html)} bytes)")

        # Extract content
        try:
            content = adapter.extract(soup, url)
            logger.debug(f"    -> Extracted: {content.title}")
            return content
        except Exception as e:
            error_context = {
                "url": url,
                "adapter": type(adapter).__name__,
                "error_type": type(e).__name__,
            }
            logger.error(f"Extraction failed: {e} | Context: {error_context}")
            raise ExtractionError(f"Failed to extract content from {url}: {e}") from e

    def _find_adapter(self, url: str) -> BaseSourceAdapter | None:
        """Find an adapter that can handle the given URL."""
        for adapter in self.adapters:
            if adapter.can_handle(url):
                return adapter
        return None

    def can_extract(self, url: str) -> bool:
        """Check if any adapter can handle the given URL.

        Args:
            url: The URL to check.

        Returns:
            True if an adapter is available for this URL.
        """
        return self._find_adapter(url) is not None

    def extract_tutorial_links(self, html: str, url: str) -> list[TutorialLink]:
        """Extract tutorial links from an index page.

        Args:
            html: Raw HTML content of the index page.
            url: The source URL.

        Returns:
            List of TutorialLink objects with url and title.

        Raises:
            ExtractionError: If no adapter can handle the URL or extraction fails.
        """
        logger.debug(f" * {inspect.currentframe().f_code.co_name} > Processing URL: {url}")

        # Find matching adapter
        adapter = self._find_adapter(url)
        if adapter is None:
            raise ExtractionError(f"No adapter available for URL: {url}")

        logger.debug(f"    -> Using adapter: {type(adapter).__name__}")

        # Parse HTML
        soup = BeautifulSoup(html, "html.parser")
        logger.debug(f"    -> Parsed HTML ({len(html)} bytes)")

        # Extract tutorial links
        try:
            tutorials = adapter.extract_tutorial_links(soup, url)
            logger.debug(f"    -> Found {len(tutorials)} tutorials")
            return tutorials
        except Exception as e:
            error_context = {
                "url": url,
                "adapter": type(adapter).__name__,
                "error_type": type(e).__name__,
            }
            logger.error(f"Tutorial extraction failed: {e} | Context: {error_context}")
            raise ExtractionError(f"Failed to extract tutorials from {url}: {e}") from e
