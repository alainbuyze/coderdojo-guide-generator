"""QR code generation for hyperlinks in markdown guides."""

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
    filename: str
    path: str
    index: int


class QRCodeGenerator:
    """Generate QR codes for URLs with configurable settings and caching."""

    def __init__(
        self,
        output_dir: Path,
        size: int = 100,
        error_correction: int = ERROR_CORRECT_M,
        box_size: int = 2,
        border: int = 2,
    ):
        """Initialize QR code generator.

        Args:
            output_dir: Directory to save QR code images.
            size: Target size in pixels (default: 100px).
            error_correction: QR error correction level (default: ERROR_CORRECT_M).
            box_size: Size of each QR code module in pixels (default: 2).
            border: Border size in modules (default: 2).
        """
        self.output_dir = output_dir / "qrcodes"
        self.size = size
        self.error_correction = error_correction
        self.box_size = box_size
        self.border = border
        self._cache: dict[str, str] = {}  # URL -> filename cache

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_qr_filename(self, url: str, index: int) -> str:
        """Generate consistent filename for a URL.

        Uses URL hash to create deterministic filenames and avoid duplicates.

        Args:
            url: The URL to generate a filename for.
            index: Numerical index for the QR code.

        Returns:
            Filename without directory path (e.g., 'qr_001_abc123.png').
        """
        # Create short hash of URL for uniqueness
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        return f"qr_{index:03d}_{url_hash}.png"

    def generate_qr_code(self, url: str, filename: str) -> Path:
        """Generate a QR code PNG for a URL.

        Args:
            url: The URL to encode in the QR code.
            filename: Output filename (without directory path).

        Returns:
            Path to the generated QR code image.

        Raises:
            Exception: If QR code generation or saving fails.
        """
        # Validate URL
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            logger.debug(f"    -> Skipping invalid URL: {url}")
            return None

        # Check cache first
        if url in self._cache:
            cached_filename = self._cache[url]
            logger.debug(f"    -> Using cached QR code for {url}: {cached_filename}")
            return self.output_dir / cached_filename

        logger.debug(f"    -> Generating QR code for {url}")

        # Create QR code
        qr = qrcode.QRCode(
            version=None,  # Auto-detect optimal version
            error_correction=self.error_correction,
            box_size=self.box_size,
            border=self.border,
        )

        qr.add_data(url)
        qr.make(fit=True)

        # Generate image
        img = qr.make_image(fill_color="black", back_color="white")

        # Resize to target size if needed
        if self.size:
            img = img.resize((self.size, self.size))

        # Save to file
        output_path = self.output_dir / filename
        img.save(output_path)

        # Cache the result
        self._cache[url] = filename

        logger.debug(f"       Saved to {output_path}")
        return output_path


def process_markdown_links(markdown: str, output_dir: Path) -> tuple[str, list[QRCodeInfo]]:
    """Find all markdown links, generate QR codes, and inject them inline.

    Args:
        markdown: Markdown content to process.
        output_dir: Guide-specific output directory (e.g., output/guide-name).

    Returns:
        Tuple of:
            - Modified markdown with QR code references injected
            - List of QRCodeInfo objects with metadata about generated codes

    Example:
        Input:  "Visit [our site](https://example.com) for more info"
        Output: "Visit [our site](https://example.com) ![](guide-name/qrcodes/qr_001.png) for more info"
    """
    if not markdown or not markdown.strip():
        logger.debug(" * process_markdown_links > No content to process")
        return markdown, []

    logger.debug(" * process_markdown_links > Processing markdown links")

    # Pattern to match markdown links: [text](url)
    link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

    # Pattern to match autolinks: <url>
    autolink_pattern = re.compile(r"<(https?://[^>]+)>")

    # Find all standard links
    standard_matches = list(link_pattern.finditer(markdown))

    # Find all autolinks
    autolink_matches = list(autolink_pattern.finditer(markdown))

    if not standard_matches and not autolink_matches:
        logger.debug("    -> No links found")
        return markdown, []

    logger.debug(f"    -> Found {len(standard_matches)} standard links, {len(autolink_matches)} autolinks")

    # Initialize generator
    generator = QRCodeGenerator(output_dir)

    # Combine all matches with their type, sorted by position
    all_matches = []
    for match in standard_matches:
        all_matches.append(("standard", match, match.start()))
    for match in autolink_matches:
        all_matches.append(("autolink", match, match.start()))

    # Sort by position in document
    all_matches.sort(key=lambda x: x[2])

    # Process each link
    qr_codes: list[QRCodeInfo] = []
    offset = 0  # Track string modifications
    guide_name = output_dir.name

    from src.core.config import get_settings
    settings = get_settings()

    for idx, (match_type, match, _) in enumerate(all_matches, start=1):
        # Extract URL based on match type
        if match_type == "standard":
            url = match.group(2)  # [text](url) -> url is group 2
        else:
            url = match.group(1)  # <url> -> url is group 1

        # Generate QR code
        filename = generator.get_qr_filename(url, idx)
        qr_path = generator.generate_qr_code(url, filename)

        # Skip if URL is invalid (generate_qr_code returns None)
        if qr_path is None:
            continue

        # Create QR code info
        qr_info = QRCodeInfo(
            url=url,
            filename=filename,
            path=str(qr_path.relative_to(output_dir)),
            index=idx,
        )
        qr_codes.append(qr_info)

        # Inject QR code reference inline after the link
        # Build path consistently with other image paths
        qr_relative_path = str(Path(guide_name) / "qrcodes" / filename)

        # Use HTML img tag for better compatibility with markdown renderers
        if settings.QRCODE_SCALE != 1.0:
            # Calculate new size
            new_size = int(100 * settings.QRCODE_SCALE)  # Base size is 100px
            qr_markdown = f' <img src="{qr_relative_path}" width="{new_size}">'
        else:
            qr_markdown = f' <img src="{qr_relative_path}">'

        # Calculate insertion position (after the link ends)
        insert_pos = match.end() + offset

        # Insert QR code reference
        markdown = markdown[:insert_pos] + qr_markdown + markdown[insert_pos:]

        # Update offset for next iteration
        offset += len(qr_markdown)

    logger.debug(f"    -> Generated {len(qr_codes)} QR codes")

    return markdown, qr_codes
