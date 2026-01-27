"""PDF printer for converting markdown guides to printable PDFs.

Uses xhtml2pdf for HTML to PDF conversion - a pure Python solution
that works reliably on Windows without external dependencies.
"""

import inspect
import logging
import re
import sys
from io import BytesIO
from pathlib import Path

from markdown import markdown
from xhtml2pdf import pisa

# Add project root to path for imports when running as script
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

from src.core.config import get_settings
from src.core.errors import GenerationError

settings = get_settings()
logger = logging.getLogger(__name__)


def detect_image_sections(md_content: str) -> dict[str, list[str]]:
    """Detect different types of image sections in markdown content.

    Analyzes headings and image patterns to categorize images for optimal layout.

    Args:
        md_content: Markdown content to analyze.

    Returns:
        Dict mapping section types to lists of image references.
        Section types: 'construction', 'connection', 'code', 'other'
    """
    sections = {
        "construction": [],
        "connection": [],
        "code": [],
        "other": [],
    }

    # Split by headings
    heading_pattern = r"^(#{2,3})\s+(.+)$"
    current_section = None
    current_type = "other"

    for line in md_content.split("\n"):
        # Check for heading
        heading_match = re.match(heading_pattern, line)
        if heading_match:
            heading_text = heading_match.group(2).lower()
            current_section = heading_text

            # Categorize section
            if any(
                keyword in heading_text
                for keyword in ["assembly", "bouw", "construction", "stap", "step"]
            ):
                current_type = "construction"
            elif any(
                keyword in heading_text
                for keyword in ["connection", "wiring", "aansluiting", "bedrading"]
            ):
                current_type = "connection"
            elif any(keyword in heading_text for keyword in ["code", "program", "software"]):
                current_type = "code"
            else:
                current_type = "other"

        # Check for image
        img_match = re.search(r"!\[([^\]]*)\]\(([^)]+)\)", line)
        if img_match and current_section:
            img_path = img_match.group(2)
            sections[current_type].append(img_path)

    return sections


def enhance_markdown_for_print(md_content: str) -> str:
    """Enhance markdown with CSS classes for print layout optimization.

    Args:
        md_content: Original markdown content.

    Returns:
        Enhanced markdown with HTML classes for layout control.
    """
    lines = []
    current_section = None
    section_type = "other"
    in_construction = False
    step_counter = 0

    heading_pattern = r"^(#{2,3})\s+(.+)$"
    img_pattern = r"!\[([^\]]*)\]\(([^)]+)\)"

    def md_img_to_html(line: str) -> str:
        """Convert markdown image syntax to HTML img tags.

        This is necessary because markdown parsers don't process markdown
        syntax inside HTML blocks (like divs).
        """
        return re.sub(
            img_pattern,
            r'<img alt="\1" src="\2">',
            line
        )

    for line in md_content.split("\n"):
        # Check for heading
        heading_match = re.match(heading_pattern, line)
        if heading_match:
            heading_text = heading_match.group(2).lower()
            current_section = heading_text

            # Reset step counter for new sections
            step_counter = 0

            # Categorize section
            if any(
                keyword in heading_text
                for keyword in ["assembly", "bouw", "construction", "stap", "step"]
            ):
                section_type = "construction"
                in_construction = True
            elif any(
                keyword in heading_text
                for keyword in ["connection", "wiring", "aansluit", "bedrading", "schema"]
            ):
                section_type = "connection"
                in_construction = False
            elif any(keyword in heading_text for keyword in ["code", "program", "software"]):
                section_type = "code"
                in_construction = False
            else:
                section_type = "other"
                in_construction = False

            lines.append(line)
            continue

        # Check for image
        img_match = re.search(img_pattern, line)
        if img_match:
            # Convert markdown images to HTML (required inside HTML blocks)
            html_line = md_img_to_html(line)

            # Wrap images with appropriate div classes
            if section_type == "construction":
                step_counter += 1
                # Wrap in construction-step div
                lines.append(f'<div class="construction-step" data-step="{step_counter}">')
                lines.append(html_line)
                lines.append("</div>")
            elif section_type == "connection":
                # Full-page connection diagrams
                lines.append('<div class="connection-diagram">')
                lines.append(html_line)
                lines.append("</div>")
            elif section_type == "code":
                # Code screenshots
                lines.append('<div class="code-image">')
                lines.append(html_line)
                lines.append("</div>")
            else:
                # Other images - convert to HTML but don't wrap
                lines.append(html_line)
        else:
            lines.append(line)

    return "\n".join(lines)


def strip_percentage_styles(md_content: str) -> str:
    """Remove percentage-based inline styles from img tags.

    xhtml2pdf doesn't support percentage values for width/height.
    This strips inline styles containing percentages from img tags.

    Args:
        md_content: Markdown/HTML content.

    Returns:
        Content with percentage styles removed from img tags.
    """
    # Pattern matches style attributes containing percentage values
    # e.g., style="width: 50%; height: auto;"
    return re.sub(
        r'(<img[^>]*)\s+style="[^"]*%[^"]*"([^>]*>)',
        r'\1\2',
        md_content
    )


def markdown_to_html(md_content: str, css_path: Path | None = None) -> str:
    """Convert markdown to HTML with print-optimized structure.

    Args:
        md_content: Markdown content to convert.
        css_path: Optional path to custom CSS file.

    Returns:
        Complete HTML document ready for PDF conversion.
    """
    # Strip percentage-based styles (xhtml2pdf doesn't support them)
    md_content = strip_percentage_styles(md_content)

    # Enhance markdown with print classes
    enhanced_md = enhance_markdown_for_print(md_content)

    # Convert to HTML
    html_body = markdown(
        enhanced_md,
        extensions=[
            "tables",
            "fenced_code",
            "codehilite",
            "nl2br",  # Preserve line breaks
        ],
    )

    # Load CSS
    css_content = ""
    if css_path and css_path.exists():
        css_content = css_path.read_text(encoding="utf-8")
    else:
        # Use default embedded CSS
        css_content = get_default_css()

    # Build complete HTML document
    html_doc = f"""<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CoderDojo Guide</title>
    <style>
{css_content}
    </style>
</head>
<body>
{html_body}
</body>
</html>"""

    return html_doc


def get_default_css() -> str:
    """Get default CSS for print layout.

    Loads CSS from resources/print.css file.

    Returns:
        CSS string with A4 portrait layout rules.
        Note: xhtml2pdf supports a subset of CSS 2.1
    """
    # Get path to resources/print.css relative to this module
    css_path = Path(__file__).parent.parent / "resources" / "print.css"

    if css_path.exists():
        return css_path.read_text(encoding="utf-8")

    # Fallback minimal CSS if file not found
    logger.warning(f"Default CSS file not found: {css_path}")
    return """
@page { size: A4 portrait; margin: 15mm 20mm; }
body { font-family: Helvetica, Arial, sans-serif; font-size: 11pt; }
img { max-width: 180mm; display: block; margin: 3mm auto; }
"""


def create_link_callback(base_path: Path):
    """Create a link callback with a specific base path for resolving relative URIs.

    Args:
        base_path: Base directory for resolving relative paths.

    Returns:
        Callback function for xhtml2pdf.
    """

    def link_callback(uri: str, rel: str) -> str:
        """Callback for xhtml2pdf to resolve resource URIs.

        Args:
            uri: The URI to resolve (image path, etc.)
            rel: Relative path (unused)

        Returns:
            Resolved absolute file path for the resource.
        """
        # Handle file:// URIs - convert back to path
        if uri.startswith("file:///"):
            # file:///D:/path -> D:/path
            return uri[8:]
        if uri.startswith("file://"):
            # file://path -> path
            return uri[7:]

        # Handle absolute paths
        path = Path(uri)
        if path.is_absolute():
            if path.exists():
                return str(path)
            return uri

        # Resolve relative paths against base_path
        # Convert backslashes to forward slashes for consistency
        uri_normalized = uri.replace("\\", "/")
        resolved = base_path / uri_normalized
        if resolved.exists():
            return str(resolved)

        # Try with original path
        resolved_original = base_path / uri
        if resolved_original.exists():
            return str(resolved_original)

        # Return as-is if not found (xhtml2pdf will show warning)
        logger.debug(f"Could not resolve URI: {uri} (base: {base_path})")
        return uri

    return link_callback


def markdown_to_pdf(
    md_content: str,
    output_path: Path,
    css_path: Path | None = None,
    base_url: str | None = None,
) -> Path:
    """Convert markdown content to PDF with print-optimized layout.

    Args:
        md_content: Markdown content to convert.
        output_path: Path where PDF should be saved.
        css_path: Optional path to custom CSS file.
        base_url: Optional base URL for resolving relative image paths.

    Returns:
        Path to the generated PDF file.

    Raises:
        GenerationError: If PDF generation fails.
    """
    logger.debug(
        f" * {inspect.currentframe().f_code.co_name} > Converting markdown to PDF: {output_path}"
    )

    try:
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert markdown to HTML
        html_content = markdown_to_html(md_content, css_path)
        logger.debug(f"    -> Generated {len(html_content)} bytes of HTML")

        # Determine base path for resolving relative URLs
        if base_url:
            # Convert file:// URI to path
            if base_url.startswith("file:///"):
                base_path = Path(base_url[8:])
            elif base_url.startswith("file://"):
                base_path = Path(base_url[7:])
            else:
                base_path = Path(base_url)
        else:
            base_path = output_path.parent

        logger.debug(f"    -> Base path for images: {base_path}")

        # Create link callback with base path
        link_callback = create_link_callback(base_path)

        # Generate PDF using xhtml2pdf
        with open(output_path, "wb") as pdf_file:
            # Create PDF
            pisa_status = pisa.CreatePDF(
                src=html_content,
                dest=pdf_file,
                encoding="utf-8",
                link_callback=link_callback,
            )

            if pisa_status.err:
                raise GenerationError(f"xhtml2pdf reported {pisa_status.err} errors")

        logger.debug(f"    -> PDF saved: {output_path}")
        return output_path

    except Exception as e:
        error_context = {
            "output_path": str(output_path),
            "error_type": type(e).__name__,
        }
        logger.error(f"PDF generation failed: {e} | Context: {error_context}")
        raise GenerationError(f"Failed to generate PDF: {e}") from e


def markdown_file_to_pdf(
    md_path: Path,
    output_path: Path | None = None,
    css_path: Path | None = None,
) -> Path:
    """Convert a markdown file to PDF.

    Args:
        md_path: Path to markdown file.
        output_path: Optional output PDF path (defaults to same name with .pdf extension).
        css_path: Optional path to custom CSS file.

    Returns:
        Path to the generated PDF file.

    Raises:
        GenerationError: If file reading or PDF generation fails.
    """
    logger.debug(f" * {inspect.currentframe().f_code.co_name} > Processing file: {md_path}")

    try:
        # Read markdown file
        if not md_path.exists():
            raise GenerationError(f"Markdown file not found: {md_path}")

        md_content = md_path.read_text(encoding="utf-8")
        logger.debug(f"    -> Read {len(md_content)} bytes")

        # Determine output path
        if output_path is None:
            output_path = md_path.with_suffix(".pdf")

        # Get base URL for resolving relative image paths
        # Use the markdown file's directory as base
        base_url = md_path.parent.as_uri()

        # Convert to PDF
        return markdown_to_pdf(md_content, output_path, css_path, base_url)

    except Exception as e:
        error_context = {
            "md_path": str(md_path),
            "error_type": type(e).__name__,
        }
        logger.error(f"Markdown file conversion failed: {e} | Context: {error_context}")
        raise GenerationError(f"Failed to convert markdown file: {e}") from e


if __name__ == "__main__":
    """Main function to print a specific markdown file to PDF."""

    # Hardcoded input file path
    input_file = Path(r"D:\Coderdojo\Projects\nezha-inventor-s-kit-for-microbit-case-61.md")

    try:
        print(f"Converting {input_file} to PDF...")
        output_path = markdown_file_to_pdf(input_file)
        print(f"Successfully generated PDF: {output_path}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
