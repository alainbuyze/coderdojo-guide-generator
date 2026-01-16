"""QR code generation for hyperlinks in markdown guides."""

import hashlib
import inspect
import logging
import re
from pathlib import Path
from typing import NamedTuple

import qrcode
from qrcode.constants import ERROR_CORRECT_M

from src.core.errors import GenerationError

logger = logging.getLogger(__name__)


class QRCodeInfo(NamedTuple):
    """Information about a generated QR code."""

    url: str
    filename: str
    path: Path
    position: int


class QRCodeGenerator:
    """Generate and manage QR codes for URLs."""

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
            output_dir: Directory to save QR code images.
            size: Target pixel size for QR code (default: 141px for 1.5cm at 300 DPI).
            error_correction: Error correction level (default: ERROR_CORRECT_M).
            box_size: Size of each QR code box in pixels (default: 3).
            border: Border size in boxes (default: 2).
        """
        self.output_dir = output_dir
        self.size = size
        self.error_correction = error_correction
        self.box_size = box_size
        self.border = border
        self.qrcode_dir = output_dir / "qrcodes"
        self.qrcode_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, Path] = {}

    def generate_qr_code(self, url: str, filename: str) -> Path:
        """Generate a QR code PNG for a URL.

        Args:
            url: The URL to encode.
            filename: The filename for the QR code image.

        Returns:
            Path to the generated QR code image.

        Raises:
            GenerationError: If QR code generation fails.
        """
        # Check cache
        if url in self._cache:
            logger.debug(f"    -> Reusing cached QR code for: {url[:50]}...")
            return self._cache[url]

        try:
            # Create QR code
            qr = qrcode.QRCode(
                version=1,  # Auto-adjust version
                error_correction=self.error_correction,
                box_size=self.box_size,
                border=self.border,
            )
            qr.add_data(url)
            qr.make(fit=True)

            # Generate image
            img = qr.make_image(fill_color="black", back_color="white")

            # Save to file
            output_path = self.qrcode_dir / filename
            img.save(str(output_path))

            # Cache the result
            self._cache[url] = output_path

            logger.debug(f"    -> Generated QR code: {filename} for {url[:50]}...")
            return output_path

        except Exception as e:
            logger.error(f"Failed to generate QR code for {url}: {e}")
            raise GenerationError(f"QR code generation failed: {e}") from e

    def get_qr_filename(self, url: str, index: int) -> str:
        """Generate a consistent filename for a URL.

        Uses a hash of the URL to create deterministic filenames,
        with an index fallback for uniqueness.

        Args:
            url: The URL to generate a filename for.
            index: Sequential index for this QR code.

        Returns:
            Filename string (e.g., "qr_001.png").
        """
        # Create a short hash of the URL for deterministic naming
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        return f"qr_{index:03d}_{url_hash}.png"


def process_markdown_links(
    markdown: str, output_dir: Path, add_qrcodes: bool = True
) -> tuple[str, list[QRCodeInfo]]:
    """Find all markdown links, generate QR codes, and inject them into markdown.

    Args:
        markdown: The markdown content to process.
        output_dir: Directory for saving QR code images.
        add_qrcodes: Whether to generate and add QR codes (default: True).

    Returns:
        Tuple of (modified_markdown, list of QRCodeInfo objects).

    Raises:
        GenerationError: If QR code processing fails.
    """
    logger.debug(f" * {inspect.currentframe().f_code.co_name} > Processing markdown links")

    if not add_qrcodes:
        logger.debug("    -> QR code generation disabled")
        return markdown, []

    try:
        # Pattern to match markdown links: [text](url)
        link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

        # Find all links
        matches = list(link_pattern.finditer(markdown))
        if not matches:
            logger.debug("    -> No links found in markdown")
            return markdown, []

        logger.debug(f"    -> Found {len(matches)} links")

        # Initialize QR code generator
        generator = QRCodeGenerator(output_dir)

        # Process links in reverse order to maintain string positions
        qr_infos: list[QRCodeInfo] = []
        modified_markdown = markdown

        for idx, match in enumerate(reversed(matches), start=1):
            link_text = match.group(1)
            url = match.group(2)
            position = match.end()

            # Generate QR code filename and create image
            filename = generator.get_qr_filename(url, len(matches) - idx + 1)
            qr_path = generator.generate_qr_code(url, filename)

            # Create relative path for markdown
            relative_path = f"qrcodes/{filename}"

            # Insert QR code image reference after the link (inline placement)
            qr_markdown = f" ![QR]({relative_path})"

            # Insert into markdown at the correct position
            modified_markdown = (
                modified_markdown[: match.end()] + qr_markdown + modified_markdown[match.end() :]
            )

            # Store info (in reverse, so we'll reverse the list at the end)
            qr_infos.append(
                QRCodeInfo(url=url, filename=filename, path=qr_path, position=position)
            )

        # Reverse qr_infos to match original link order
        qr_infos.reverse()

        logger.debug(f"    -> Added {len(qr_infos)} QR codes to markdown")
        return modified_markdown, qr_infos

    except Exception as e:
        logger.error(f"Failed to process markdown links: {e}")
        raise GenerationError(f"Link processing failed: {e}") from e
