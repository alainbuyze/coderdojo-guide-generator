"""QR code generator for hyperlinks in markdown documents."""

import hashlib
import logging
import re
from pathlib import Path
from typing import NamedTuple

import qrcode
from qrcode.constants import ERROR_CORRECT_M

logger = logging.getLogger(__name__)


class QRCodeInfo(NamedTuple):
    """Information about a generated QR code."""

    url: str
    qr_path: str
    position: int


class QRCodeGenerator:
    """Generate and manage QR codes for URLs.

    Creates small, scannable QR codes suitable for printed documents.
    Implements caching to avoid regenerating codes for duplicate URLs.
    """

    def __init__(
        self,
        output_dir: Path,
        size: int = 141,
        error_correction=ERROR_CORRECT_M,
        box_size: int = 3,
        border: int = 2,
    ):
        """Initialize QR code generator.

        Args:
            output_dir: Base output directory (qrcodes/ subdirectory will be created here).
            size: Target size in pixels (default: 141px = 1.5cm at 300 DPI).
            error_correction: QR code error correction level (default: MEDIUM).
            box_size: Pixels per QR code module (default: 3).
            border: Border size in modules (default: 2).
        """
        self.output_dir = output_dir
        self.qrcode_dir = output_dir / "qrcodes"
        self.size = size
        self.error_correction = error_correction
        self.box_size = box_size
        self.border = border
        self._cache: dict[str, str] = {}  # URL -> filename mapping

        # Ensure qrcodes directory exists
        self.qrcode_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"QR code output directory: {self.qrcode_dir}")

    def generate_qr_code(self, url: str) -> Path:
        """Generate a QR code PNG for a URL.

        If the URL has been processed before, returns the cached filename.

        Args:
            url: URL to encode in the QR code.

        Returns:
            Path to the generated QR code image (relative to output_dir).

        Raises:
            Exception: If QR code generation fails.
        """
        # Check cache first
        if url in self._cache:
            cached_filename = self._cache[url]
            logger.debug(f"    -> Using cached QR code for {url[:50]}...")
            return Path("qrcodes") / cached_filename

        # Generate deterministic filename from URL hash
        filename = self._get_qr_filename(url)
        qr_path = self.qrcode_dir / filename

        # Skip if file already exists
        if qr_path.exists():
            logger.debug(f"    -> QR code already exists: {filename}")
            self._cache[url] = filename
            return Path("qrcodes") / filename

        # Generate QR code
        try:
            qr = qrcode.QRCode(
                version=1,  # Auto-adjust version based on data
                error_correction=self.error_correction,
                box_size=self.box_size,
                border=self.border,
            )
            qr.add_data(url)
            qr.make(fit=True)

            # Create image
            img = qr.make_image(fill_color="black", back_color="white")

            # Resize to target size if needed
            if img.size[0] != self.size:
                img = img.resize((self.size, self.size))

            # Save PNG
            img.save(qr_path)
            logger.debug(f"    -> Generated QR code: {filename}")

            # Cache the result
            self._cache[url] = filename

            return Path("qrcodes") / filename

        except Exception as e:
            logger.error(f"Failed to generate QR code for {url}: {e}")
            raise

    def _get_qr_filename(self, url: str) -> str:
        """Generate a deterministic filename for a URL.

        Uses SHA256 hash of the URL to create a unique, consistent filename.

        Args:
            url: URL to generate filename for.

        Returns:
            Filename in format: qr_{hash}.png
        """
        # Create hash of URL
        url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
        return f"qr_{url_hash}.png"


def process_markdown_links(
    markdown: str, output_dir: Path, add_qrcodes: bool = True
) -> tuple[str, list[QRCodeInfo]]:
    """Find all markdown links and inject QR codes inline.

    Detects markdown links in format [text](url) and adds a QR code image
    immediately after each link: [text](url) ![](qrcodes/qr_xxx.png)

    Args:
        markdown: Input markdown content.
        output_dir: Output directory for QR codes.
        add_qrcodes: Whether to actually generate and inject QR codes.

    Returns:
        Tuple of (modified_markdown, qr_code_info_list).
        If add_qrcodes is False, returns original markdown and empty list.

    Raises:
        Exception: If QR code generation fails.
    """
    if not add_qrcodes:
        return markdown, []

    if not markdown or not markdown.strip():
        return markdown, []

    # Pattern to match markdown links: [text](url)
    # Captures: group 1 = link text, group 2 = URL
    link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

    generator = QRCodeGenerator(output_dir)
    qr_info_list: list[QRCodeInfo] = []

    # Find all links
    matches = list(link_pattern.finditer(markdown))

    if not matches:
        logger.debug("    -> No links found in markdown")
        return markdown, []

    logger.debug(f"    -> Found {len(matches)} links in markdown")

    # Process matches in reverse order to preserve positions
    modified_markdown = markdown
    offset = 0

    for match in matches:
        link_text = match.group(1)
        url = match.group(2)
        original_link = match.group(0)
        start_pos = match.start() + offset

        try:
            # Generate QR code
            qr_path = generator.generate_qr_code(url)

            # Create QR code markdown (small inline image)
            qr_markdown = f" ![QR]({qr_path})"

            # Inject QR code after the link
            end_pos = match.end() + offset
            modified_markdown = (
                modified_markdown[:end_pos] + qr_markdown + modified_markdown[end_pos:]
            )

            # Update offset for next iteration
            offset += len(qr_markdown)

            # Record info
            qr_info_list.append(
                QRCodeInfo(url=url, qr_path=str(qr_path), position=start_pos)
            )

            logger.debug(f"    -> Added QR code for: {url[:60]}...")

        except Exception as e:
            logger.warning(f"    -> Failed to add QR code for {url}: {e}")
            # Continue processing other links

    logger.debug(f"    -> Added {len(qr_info_list)} QR codes")
    return modified_markdown, qr_info_list
