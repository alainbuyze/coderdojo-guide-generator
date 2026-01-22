"""Catalog generator for creating a summary document of all project guides.

This module parses existing markdown guides and generates a catalog document
containing a table of contents and summary entries for each project.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ProjectSummary:
    """Summary data extracted from a project guide.

    Attributes:
        title: Project title (H1 heading).
        introduction: Introduction paragraph text.
        main_image: Path to main/first image, if any.
        file_path: Path to the source markdown file.
        slug: URL-friendly identifier for anchor links.
    """

    title: str
    introduction: str
    main_image: str | None
    file_path: Path
    slug: str


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug for anchor links.

    Args:
        text: Text to convert.

    Returns:
        Lowercase slug with hyphens.
    """
    slug = text.lower()
    slug = re.sub(r"[_\s]+", "-", slug)
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    return slug


def parse_guide_for_catalog(md_path: Path) -> ProjectSummary | None:
    """Parse a markdown guide and extract catalog summary data.

    Extracts the H1 title, introduction section content, and first image
    from a markdown guide file.

    Args:
        md_path: Path to the markdown file.

    Returns:
        ProjectSummary with extracted data, or None if parsing fails.
    """
    try:
        content = md_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning(f"Failed to read {md_path}: {e}")
        return None

    # Extract H1 title
    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if not title_match:
        logger.warning(f"No H1 title found in {md_path}")
        return None

    title = title_match.group(1).strip()

    # Extract introduction section (## Introductie or ## Introduction)
    # Look for content between Introductie heading and next heading
    intro_pattern = r"##\s+(?:Introductie|Introduction)\s*(?:\u200B|\u200C|\u200D)?\s*\n(.*?)(?=\n###\s+(?:Benodigde\smaterialen|Materials\sRequired)\s*(?:\u200B|\u200C|\u200D)?\s*\n|\n##|\n#|\Z)"
    intro_match = re.search(intro_pattern, content, re.DOTALL | re.IGNORECASE)

    introduction = ""
    if intro_match:
        intro_content = intro_match.group(1).strip()
        # Extract text, skipping images, hyperlinks, img tags and empty lines
        intro_lines = []
        for line in intro_content.split("\n"):
            line = line.strip()
            # Skip image lines, empty lines, and lines with only images/img tags
            if line and not line.startswith("![") and not line.startswith("<img"):
                # Remove markdown hyperlinks [text](url) -> text
                line = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', line)
                # Remove HTML img tags
                line = re.sub(r'<img[^>]*>', '', line)
                # Remove any remaining HTML-like tags
                line = re.sub(r'<[^>]*>', '', line)
                if line:  # Only add if line still has content after cleanup
                    intro_lines.append(line)
        introduction = " ".join(intro_lines)
        # Limit length for catalog display
        if len(introduction) > 500:
            introduction = introduction[:497] + "..."

    # Extract first image from introduction section
    intro_section_pattern = r"##\s+(?:Introductie|Introduction)\s*(?:\u200B|\u200C|\u200D)?\s*\n(.*?)(?=\n###\s+(?:Benodigde\smaterialen|Materials\sRequired)\s*(?:\u200B|\u200C|\u200D)?\s*\n|\n##|\n#|\Z)"
    intro_section_match = re.search(intro_section_pattern, content, re.DOTALL | re.IGNORECASE)

    main_image = None
    if intro_section_match:
        intro_section = intro_section_match.group(1)
        image_match = re.search(r"!\[([^\]]*)\]\(([^)]+)\)", intro_section)
        if image_match:
            image_path = image_match.group(2)
            # Store image path as-is for markdown formatting in catalog
            main_image = image_path

    slug = slugify(title)

    return ProjectSummary(
        title=title,
        introduction=introduction,
        main_image=main_image,
        file_path=md_path,
        slug=slug,
    )


def generate_catalog(
    guides_dir: Path,
    output_path: Path | None = None,
    title: str = "Project Catalogus",
) -> Path:
    """Generate a catalog markdown document from all guides in a directory.

    Scans the directory for markdown files, parses each for summary data,
    and generates a catalog with table of contents and project entries.

    Args:
        guides_dir: Directory containing markdown guide files.
        output_path: Output path for the catalog file. Defaults to
            guides_dir/catalog.md.
        title: Title for the catalog document.

    Returns:
        Path to the generated catalog file.

    Raises:
        ValueError: If no valid guides are found in the directory.
    """
    if output_path is None:
        output_path = guides_dir / "catalog.md"

    # Find all markdown files (excluding catalog itself)
    md_files = [
        f for f in guides_dir.glob("*.md")
        if f.name != "catalog.md" and not f.name.startswith(".")
    ]

    if not md_files:
        raise ValueError(f"No markdown files found in {guides_dir}")

    logger.info(f"Found {len(md_files)} markdown files")

    # Sort files alphabetically by name
    md_files.sort(key=lambda f: f.name.lower())

    # Parse each guide
    summaries: list[ProjectSummary] = []
    for md_file in md_files:
        summary = parse_guide_for_catalog(md_file)
        if summary:
            summaries.append(summary)
        else:
            logger.warning(f"Skipping {md_file.name}: could not parse")

    if not summaries:
        raise ValueError("No valid guides found to include in catalog")

    # Sort by title
    summaries.sort(key=lambda s: s.title.lower())

    # Generate catalog content
    parts = []

    # Title
    parts.append(f"# {title}\n")

    # Table of contents
    parts.append("\n## Inhoudsopgave\n")
    for i, summary in enumerate(summaries, 1):
        parts.append(f"{i}. [{summary.title}](#{summary.slug})\n")

    # Project entries
    for summary in summaries:
        # Page break before each project
        parts.append("\n---\n")
        parts.append('\n<div style="page-break-before: always;"></div>\n')

        # Project title with anchor
        parts.append(f"\n## {summary.title} {{#{summary.slug}}}\n")

        # Main image if available
        if summary.main_image:
            # Make image path relative to catalog location
            # Since catalog is in same dir as guides, use guide's subdirectory
            guide_name = summary.file_path.stem
            image_path = summary.main_image
            # If the image path doesn't include the guide subdirectory, add it
            if not image_path.startswith(guide_name):
                image_path = f"{guide_name}/{image_path}"
            parts.append(f"\n![{summary.title}]({image_path})\n")

        # Introduction
        if summary.introduction:
            parts.append(f"\n{summary.introduction}\n")

        # Link to full guide
        # guide_link = summary.file_path.name
        # parts.append(f"\n📄 [Volledige handleiding →]({guide_link})\n")

    # Combine and write
    catalog_content = "".join(parts)

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(catalog_content, encoding="utf-8")
    logger.info(f"Catalog generated: {output_path}")

    return output_path


if __name__ == "__main__":
    import sys
    # Default input directory
    default_input = r"D:\Coderdojo\Projects"
    # Use command line argument or default
    input_dir = sys.argv[1] if len(sys.argv) > 1 else default_input
    try:
        catalog_path = generate_catalog(Path(input_dir))
        print(f"✅ Catalog generated successfully: {catalog_path}")
    except Exception as e:
        print(f"❌ Error generating catalog: {e}")
        sys.exit(1)
