"""Markdown generator for creating printable guides."""

import inspect
import logging
import re
from pathlib import Path

from bs4 import Tag
from markdownify import MarkdownConverter

from src.core.config import get_settings
from src.core.errors import GenerationError
from src.qrcode_processor import process_markdown_links
from src.sources.base import ExtractedContent

settings = get_settings()
logger = logging.getLogger(__name__)


class GuideMarkdownConverter(MarkdownConverter):
    """Custom Markdown converter that preserves image URLs.

    Can optionally use local image paths from an image map.
    """

    def __init__(self, image_map: dict[str, str] | None = None, **kwargs):
        """Initialize converter with optional image mapping.

        Args:
            image_map: Dict mapping remote URLs to local paths.
            **kwargs: Arguments passed to parent MarkdownConverter.
        """
        super().__init__(**kwargs)
        self.image_map = image_map or {}

    def convert_img(
        self, el: Tag, text: str = "", convert_as_inline: bool = False, **kwargs
    ) -> str:
        """Convert img tag to markdown, using local path if available.

        Args:
            el: The img element.
            text: Text content (usually empty for images).
            convert_as_inline: Whether to convert as inline element.
            **kwargs: Additional arguments passed by markdownify.
        """
        src = el.get("src", "")
        alt = el.get("alt", "")
        title = el.get("title", "")

        # Check for local path in image map
        local_path = self.image_map.get(src)
        if local_path:
            src = local_path

        # Apply image scaling if not 1.0
        scale = settings.IMAGE_SCALE
        if scale != 1.0:
            # Calculate new dimensions if width/height attributes exist
            width = el.get("width")
            height = el.get("height")

            if width:
                try:
                    new_width = int(float(width) * scale)
                    src = f"{src}|{new_width}"
                except (ValueError, TypeError):
                    pass

            if height:
                try:
                    new_height = int(float(height) * scale)
                    if "|" in src:
                        src = f"{src}x{new_height}"
                    else:
                        src = f"{src}|x{new_height}"
                except (ValueError, TypeError):
                    pass

        if title:
            return f'![{alt}]({src} "{title}")'
        return f"![{alt}]({src})"


def html_to_markdown(html: str | Tag, image_map: dict[str, str] | None = None) -> str:
    """Convert HTML to Markdown using custom converter.

    Args:
        html: HTML string or BeautifulSoup Tag.
        image_map: Optional dict mapping remote URLs to local paths.

    Returns:
        Markdown formatted string.
    """
    if isinstance(html, Tag):
        html = str(html)

    converter = GuideMarkdownConverter(
        image_map=image_map,
        heading_style="ATX",
        bullets="-",
        code_language="",
        escape_underscores=False,
    )

    md = converter.convert(html)

    # Clean up excessive whitespace
    md = re.sub(r"\n{3,}", "\n\n", md)

    # Ensure space before markdown links when preceded by a word character
    # e.g., "de[link]" -> "de [link]"
    md = re.sub(r"(\w)\[([^\]]+)\]\(", r"\1 [\2](", md)

    # Ensure space after markdown links when followed by a word character
    # e.g., "[link](url)word" -> "[link](url) word"
    md = re.sub(r"\]\(([^)]+)\)(\w)", r"](\1) \2", md)

    return md.strip()


def build_image_map(content: ExtractedContent) -> dict[str, str]:
    """Build a mapping from remote URLs to local paths.

    Prefers enhanced_path over local_path if available.

    Args:
        content: Extracted content with images.

    Returns:
        Dict mapping remote src URLs to local paths.
    """
    image_map = {}
    for image in content.images:
        src = image.get("src", "")
        if not src:
            continue

        # Prefer enhanced path, fall back to local path
        local_path = image.get("enhanced_path") or image.get("local_path")
        if local_path:
            # Use forward slashes for markdown compatibility
            # Backslashes cause escape sequence issues in markdown
            image_map[src] = local_path.replace("\\", "/")

    return image_map


def generate_table_of_contents(markdown: str) -> str:
    """Generate a table of contents from all header 2 entries in the markdown.

    Args:
        markdown: The markdown content to process.

    Returns:
        Markdown content with table of contents added after the title.
    """
    # Find all header 2 entries
    headers = re.findall(r'^## (.+)$', markdown, flags=re.MULTILINE)

    if not headers:
        return markdown

    # Generate table of contents
    toc_lines = ["## Inhoudsopgave\n"]
    for header in headers:
        # Create anchor link by converting to lowercase and replacing spaces with hyphens
        anchor = header.lower().replace(' ', '-').replace('/', '').replace('(', '').replace(')', '')
        toc_lines.append(f"- [{header}](#{anchor})")

    toc = "\n".join(toc_lines) + "\n\n"

    # Insert table of contents after the main title (first # header)
    title_pattern = r'^(# .+)$'
    if re.search(title_pattern, markdown, flags=re.MULTILINE):
        markdown = re.sub(title_pattern, r'\1\n\n' + toc, markdown, count=1, flags=re.MULTILINE)

    return markdown


def post_process_markdown(markdown: str) -> str:
    """Apply post-processing fixes to the generated markdown.

    Args:
        markdown: The markdown content to process.

    Returns:
        The processed markdown content.
    """
    # Remove any non-displayable characters (control characters except common whitespace)
    # Keep: \t (tab), \n (newline), \r (carriage return)
    # Remove: other control characters (0x00-0x1F, 0x7F-0x9F) except the ones above
    markdown = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', markdown)

    # Remove paragraph containing "Invoering" just after header 1
    # Pattern: # Header\n\n> Invoering\n\n or # Header\n\nInvoering\n\n
    markdown = re.sub(r'(^# .+\n\n)>? ?Invoering\n\n', r'\1', markdown, flags=re.MULTILINE)

    # Change title "Stap 1" to "Programmering"
    markdown = re.sub(r'^# Stap 1', '# Programmering', markdown, flags=re.MULTILINE)

    # Change specific hyperlink from elecfreaks.com to shop.elecfreaks.com
    old_url = "https://www.elecfreaks.com/nezha-inventor-s-kit-for-micro-bit-without-micro-bit-board.html"
    new_url = "https://shop.elecfreaks.com/products/elecfreaks-micro-bit-nezha-48-in-1-inventors-kit-without-micro-bit-board"
    markdown = markdown.replace(old_url, new_url)

    # Convert specific header 3 headers to header 2
    headers_to_convert = [
        'Programmering',
        'Benodigde materialen',
        'Montage stappen',
        'Aansluitschema',
        'Resultaat'
    ]

    for header in headers_to_convert:
        # Replace ### Header with ## Header, being more flexible with invisible characters
        replacement = f'## {header}'
        # First, clean the specific line from invisible characters, then apply the pattern
        lines = markdown.split('\n')
        for i, line in enumerate(lines):
            if re.match(rf'^### {re.escape(header)}', line):
                # Clean the line from any remaining invisible characters
                clean_line = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', line)
                clean_line = re.sub(r'[\u200B-\u200D\uFEFF]', '', clean_line)  # Zero-width characters
                if re.match(rf'^### {re.escape(header)}\s*$', clean_line):
                    lines[i] = replacement
        markdown = '\n'.join(lines)

    # Scale down non-QR code images that appear after specific instruction text
    lines = markdown.split('\n')
    for i, line in enumerate(lines):
        # Check for instruction text followed by image on next line
        if 'Klik op "Geavanceerd" in de MakeCode-lade om meer keuzes te zien.' in line:
            # Check if next line contains an image (not QR code)
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                # Match image pattern that doesn't have qrcode class
                img_match = re.match(r'^!\[\]\(([^)]+)\)$', next_line.strip())
                if img_match and 'qrcode' not in next_line.lower():
                    # Add scaling to make image smaller (similar to QR code size)
                    scaled_img = f'![]({img_match.group(1)}|150)'
                    lines[i + 1] = scaled_img
    markdown = '\n'.join(lines)

    # Add table of contents with all header 2 entries
    markdown = generate_table_of_contents(markdown)

    return markdown


def generate_guide(
    content: ExtractedContent, output_dir: Path | None = None, add_qrcodes: bool = True
    ) -> str:
    """Generate a Markdown guide from extracted content.

    Uses local image paths if available (from downloader/enhancer).
    Optionally adds QR codes for all hyperlinks in the guide.

    Args:
        content: Structured content from extraction.
        output_dir: Output directory for QR codes (required if add_qrcodes is True).
        add_qrcodes: Whether to generate QR codes for hyperlinks (default: True).

    Returns:
        Markdown formatted guide string.

    Raises:
        GenerationError: If guide generation fails.
    """
    logger.debug(f" * {inspect.currentframe().f_code.co_name} > Generating guide: {content.title}")

    try:
        parts = []

        # Build image map for local path substitution
        image_map = build_image_map(content)
        if image_map:
            logger.debug(f"    -> Using {len(image_map)} local image paths")

        # Title
        parts.append(f"# {content.title}\n")

        # Metadata section (optional)
        if content.metadata.get("description"):
            parts.append(f"> {content.metadata['description']}\n")

        # Language indicator if translated
        if content.metadata.get("language") and content.metadata.get("language") != "en":
            lang = content.metadata["language"]
            logger.debug(f"    -> Content language: {lang}")

        # Sections
        for section in content.sections:
            heading = section.get("heading", "")
            level = section.get("level", 2)
            section_content = section.get("content", [])

            # Skip section if heading duplicates the title
            if heading and heading == content.title:
                continue

            if heading:
                prefix = "#" * level
                parts.append(f"\n{prefix} {heading}\n")

            # Convert each content element
            for element in section_content:
                if isinstance(element, Tag):
                    md = html_to_markdown(element, image_map=image_map)
                    if md:
                        parts.append(md + "\n")

        # Combine all parts
        guide = "\n".join(parts)

        # Final cleanup
        guide = re.sub(r"\n{3,}", "\n\n", guide)

        logger.debug(f"    -> Generated {len(guide)} bytes of Markdown")

        # Apply post-processing fixes
        guide = post_process_markdown(guide)

        # Add QR codes for hyperlinks if requested
        if add_qrcodes and output_dir:
            logger.debug("    -> Processing hyperlinks for QR codes")
            guide, qr_codes = process_markdown_links(guide, output_dir)
            if qr_codes:
                logger.debug(f"    -> Added {len(qr_codes)} QR codes")

        return guide

    except Exception as e:
        error_context = {
            "title": content.title,
            "sections": len(content.sections),
            "error_type": type(e).__name__,
        }
        logger.error(f"Generation failed: {e} | Context: {error_context}")
        raise GenerationError(f"Failed to generate guide: {e}") from e


def save_guide(guide: str, output_path: Path) -> Path:
    """Save a guide to a file.

    Args:
        guide: Markdown content to save.
        output_path: Path to save the guide to.

    Returns:
        The path where the guide was saved.

    Raises:
        GenerationError: If saving fails.
    """
    logger.debug(f" * {inspect.currentframe().f_code.co_name} > Saving to: {output_path}")

    try:
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        output_path.write_text(guide, encoding="utf-8")
        logger.debug(f"    -> Saved {len(guide)} bytes")

        return output_path

    except Exception as e:
        error_context = {
            "path": str(output_path),
            "error_type": type(e).__name__,
        }
        logger.error(f"Save failed: {e} | Context: {error_context}")
        raise GenerationError(f"Failed to save guide: {e}") from e
