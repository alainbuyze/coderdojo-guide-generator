"""CoderDojo Guide Generator CLI - Create printable guides from online tutorials.

This module provides a comprehensive command-line interface for converting online tutorials
into printable guides with enhanced images, translations, and QR codes. The tool supports
both single tutorial processing and batch processing of multiple tutorials.

Features:
- Download and extract content from supported tutorial websites
- Replace MakeCode screenshots with localized versions
- Download and enhance images using AI upscaling
- Translate content to Dutch
- Generate QR codes for hyperlinks
- Create printable PDF versions with optimized layouts
- Batch processing with resume capability
- Re-process guides using existing images (skip download/enhance)
- Progress tracking and detailed logging

Supported Sources:
- wiki.elecfreaks.com - Elecfreaks Wiki tutorials

Basic Usage:
    # Generate a guide from a single tutorial
    uv run python -m src.cli generate --url "https://wiki.elecfreaks.com/en/microbit/..."

    # Process all tutorials from an index page
    uv run python -m src.cli batch --index "https://wiki.elecfreaks.com/en/microbit/building-blocks/nezha-inventors-kit/"

    # Convert a markdown guide to PDF
    uv run python -m src.cli print --input output/tutorial.md

Examples:
    # Basic single tutorial processing
    uv run python -m src.cli generate `
        --url "https://wiki.elecfreaks.com/en/microbit/building-blocks/nezha-inventors-kit/case-01/" `
        --output ./guides

    # Single tutorial with all features enabled (default behavior)
    uv run python -m src.cli generate `
        --url "https://wiki.elecfreaks.com/en/microbit/building-blocks/nezha-inventors-kit/Nezha_Inventor_s_kit_for_microbit_case_69" `
        --output ./guides `
        --verbose

    # Single tutorial skipping optional features
    uv run python -m src.cli generate `
        --url "https://wiki.elecfreaks.com/en/microbit/building-blocks/nezha-inventors-kit/case-03/" `
        --output ./guides `
        --no-enhance `
        --no-translate `
        --no-qrcode `
        --no-makecode

    # Re-process tutorial using existing downloaded/enhanced images
    uv run python -m src.cli generate `
        --url "https://wiki.elecfreaks.com/en/microbit/building-blocks/nezha-inventors-kit/Nezha_Inventor_s_kit_for_microbit_case_01/" `
        --output "D:/Coderdojo/Projects" `
        --no-download

    # List all tutorials on an index page
    uv run python -m src.cli batch `
        --index "https://wiki.elecfreaks.com/en/microbit/building-blocks/nezha-inventors-kit/" `
        --list-only

    # Batch process all tutorials with resume capability
    uv run python -m src.cli batch `
        --index "https://wiki.elecfreaks.com/en/microbit/building-blocks/nezha-inventors-kit/" `
        --output ./guides `
        --verbose

    # Resume interrupted batch processing
    uv run python -m src.cli batch `
        --index "https://wiki.elecfreaks.com/en/microbit/building-blocks/nezha-inventors-kit/" `
        --output ./guides `
        --resume `
        --verbose

    # Batch processing with disabled features for faster processing
    uv run python -m src.cli batch `
        --index "https://wiki.elecfreaks.com/en/microbit/building-blocks/nezha-inventors-kit/" `
        --output ./guides `
        --no-enhance `
        --no-translate `
        --no-qrcode

    # Re-process batch using existing downloaded/enhanced images
    uv run python -m src.cli batch `
        --index "https://wiki.elecfreaks.com/en/microbit/building-blocks/nezha-inventors-kit/" `
        --output ./guides `
        --no-download

    # Convert markdown guide to PDF with default settings
    uv run python -m src.cli print `
        --input ./guides/case-01.md

    # Convert to PDF with custom output path
    uv run python -m src.cli print `
        --input ./guides/case-01.md `
        --output ./printable/case-01-tutorial.pdf

    # Convert to PDF with custom CSS styling
    uv run python -m src.cli print `
        --input ./guides/case-01.md `
        --css ./custom-print-styles.css

    # Convert all markdown files in a directory to PDFs
    uv run python -m src.cli print-all --input ./guides

    # Convert all markdown files to specific output directory
    uv run python -m src.cli print-all -i ./guides -o ./pdfs

    # Convert all markdown files with custom CSS styling
    uv run python -m src.cli print-all --input ./guides --css ./custom-print-styles.css

    # Show supported sources
    uv run python -m src.cli sources

Output Structure:
    Single tutorial:
    <output>/
        <guide-name>.md              # Generated markdown guide
        <guide-name>/
            images/                  # Downloaded and enhanced images
            qrcodes/                 # QR codes for hyperlinks (if enabled)

    Batch processing:
    <output>/
        guide-1.md
        guide-1/images/
        guide-2.md
        guide-2/images/
        ...
        .batch_state.json           # Resume state (auto-cleaned on success)

Pipeline Stages:
    1. Fetch: Download HTML content from the tutorial URL
    2. Extract: Parse and extract structured content (title, sections, images)
    3. MakeCode: Replace MakeCode screenshots with Dutch versions (if enabled)
    4. Download: Fetch all images and store locally (or use existing if --no-download)
    5. Enhance: AI-enhance images for better quality (if enabled, skipped with --no-download)
    6. Translate: Convert content to Dutch (if enabled)
    7. Generate: Create markdown guide with local image references
    8. QR Codes: Generate QR codes for hyperlinks (if enabled)
    9. Save: Write guide to filesystem

Error Handling:
- Critical errors (fetch, extract, generate, save) will stop processing
- Non-critical errors (download, enhance, translate, makecode) log warnings and continue
- Batch processing tracks failed tutorials and can resume from interruptions
- Verbose mode provides detailed error information and debugging output

Configuration:
The tool uses environment variables and configuration files for settings:
- RATE_LIMIT_SECONDS: Delay between batch processing requests
- MAKECODE_REPLACE_ENABLED: Enable/disable MakeCode screenshot replacement
- MAKECODE_LANGUAGE: Target language for MakeCode replacements
- LOG_LEVEL: Default logging level (DEBUG, INFO, WARNING, ERROR)

Dependencies:
- playwright: Web scraping and browser automation
- upscayl: AI image enhancement (optional)
- weasyprint: PDF generation (for print command)
- click: Command-line interface framework
- rich: Terminal formatting and progress display
"""

import asyncio
import json
import re
import shutil
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table

from src.catalog import generate_catalog
from src.core.config import get_settings
from src.core.logging import setup_logging
from src.downloader import download_images
from src.downloader import generate_filename as downloader_generate_filename
from src.enhancer import enhance_all_images
from src.extractor import ContentExtractor
from src.generator import generate_guide, save_guide
from src.makecode_replacer import replace_makecode_screenshots
from src.scraper import fetch_page, get_browser
from src.sources.base import ExtractedContent
from src.translator import translate_content

# Note: printer module imported lazily in print_guide() and print_all() to avoid WeasyPrint GTK3 dependency
# when running commands that don't need PDF generation

console = Console()

def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug.

    Args:
        text: Text to convert.

    Returns:
        Lowercase slug with hyphens.
    """
    # Convert to lowercase and replace spaces/underscores with hyphens
    slug = text.lower()
    slug = re.sub(r"[_\s]+", "-", slug)
    # Remove non-alphanumeric characters (except hyphens)
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    # Remove multiple consecutive hyphens
    slug = re.sub(r"-+", "-", slug)
    # Remove leading/trailing hyphens
    slug = slug.strip("-")
    return slug

def get_output_filename(url: str, title: str) -> str:
    """Generate output filename from URL or title.

    Args:
        url: Source URL.
        title: Page title.

    Returns:
        Filename without extension.
    """
    # Try to get case name from URL
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    last_segment = path.split("/")[-1] if path else ""

    if last_segment and "case" in last_segment.lower():
        return slugify(last_segment)

    # Fall back to title
    return slugify(title)[:60]


def extract_case_number(url: str) -> str | None:
    """Extract case number from URL (e.g., '01' from 'case_01' or 'case-01').

    Args:
        url: Tutorial URL to parse.

    Returns:
        Case number as string (e.g., '01', '12') or None if not found.
    """
    parsed = urlparse(url)
    path = parsed.path.lower()
    match = re.search(r'case[_-]?(\d+)', path)
    return match.group(1) if match else None


def get_project_filename(case_number: str, title: str) -> str:
    """Generate filename like 'Project 01 - Title' with ASCII-only chars.

    Args:
        case_number: Case number string (e.g., '01').
        title: Translated title to include in filename.

    Returns:
        Filename in format 'Project XX - Title' with ASCII-safe characters.
    """
    # Strip "Project XX:" prefix from title to avoid duplication
    title = re.sub(r'^[Pp]roject\s*\d+[:\s]*', '', title).strip()
    # Normalize and convert to ASCII
    normalized = unicodedata.normalize('NFKD', title)
    ascii_title = normalized.encode('ascii', 'ignore').decode('ascii')
    # Clean up the title - keep alphanumeric, spaces, and hyphens
    ascii_title = re.sub(r'[^\w\s-]', '', ascii_title).strip()
    # Truncate if too long (keep room for "Project XX - ")
    if len(ascii_title) > 50:
        ascii_title = ascii_title[:50].rsplit(' ', 1)[0]
    return f"Project {case_number} - {ascii_title}"


def rename_guide_directory(
    old_dir: Path,
    new_name: str,
    output_dir: Path,
    markdown_content: str
) -> tuple[Path, str]:
    """Rename guide directory and update markdown paths.

    Args:
        old_dir: Current guide directory path.
        new_name: New name for the directory.
        output_dir: Parent output directory.
        markdown_content: Markdown content with paths to update.

    Returns:
        Tuple of (new_directory_path, updated_markdown_content).
    """
    new_dir = output_dir / new_name
    old_name = old_dir.name

    # Rename directory if it exists and name changed
    if old_dir.exists() and old_name != new_name:
        # Remove existing target directory if it exists (allows overwriting)
        if new_dir.exists():
            shutil.rmtree(new_dir)
        old_dir.rename(new_dir)

    # Update image/qrcode paths in markdown
    updated_markdown = markdown_content.replace(
        f"{old_name}/", f"{new_name}/"
    )

    return new_dir, updated_markdown


def use_existing_images(content: ExtractedContent, guide_subdir: Path) -> ExtractedContent:
    """Use existing downloaded/enhanced images instead of downloading.

    Scans the images directory for existing files and populates local_path/enhanced_path
    on the content images. This allows re-running the pipeline without re-downloading.

    Args:
        content: Extracted content with images to process.
        guide_subdir: Guide-specific output directory (e.g., output/guide-name).

    Returns:
        Updated ExtractedContent with local_path/enhanced_path set for existing images.
    """
    settings = get_settings()
    images_dir = guide_subdir / settings.IMAGE_OUTPUT_DIR
    guide_name = guide_subdir.name

    if not images_dir.exists():
        console.print(f"[yellow]Warning:[/yellow] Images directory not found: {images_dir}")
        return content

    # Build a set of existing files for quick lookup
    existing_files = {f.name: f for f in images_dir.iterdir() if f.is_file()}

    for idx, image in enumerate(content.images):
        # Skip images already replaced with Dutch MakeCode screenshots
        if image.get("replaced_with_dutch"):
            continue

        url = image.get("src", "")
        if not url:
            continue

        alt = image.get("alt", "")
        filename = downloader_generate_filename(url, alt, idx)
        stem = Path(filename).stem
        suffix = Path(filename).suffix

        # Check for enhanced version first
        enhanced_filename = f"{stem}_enhanced{suffix}"
        if enhanced_filename in existing_files:
            # Set enhanced_path (relative path for markdown)
            image["enhanced_path"] = str(Path(guide_name) / settings.IMAGE_OUTPUT_DIR / enhanced_filename)
            image["local_path"] = image["enhanced_path"]  # Also set local_path for compatibility
        elif filename in existing_files:
            # Fall back to original
            image["local_path"] = str(Path(guide_name) / settings.IMAGE_OUTPUT_DIR / filename)

    return content


async def _generate(
    url: str, output: str, verbose: bool, no_enhance: bool, no_translate: bool, no_qrcode: bool, no_makecode: bool, no_download: bool
    ) -> None:
    """Generate a guide from a single tutorial URL.

    Executes the full pipeline: fetch → extract → download images → enhance → translate → generate → QR codes.
    Executes the full pipeline: fetch → extract → replace MakeCode → download images → enhance → translate → generate.
    Each stage handles errors gracefully, with warnings for non-critical failures.

    Args:
        url: Tutorial URL to process (must be from a supported source).
        output: Output directory path for the generated guide and images.
        verbose: Enable verbose/debug logging output.
        no_enhance: Skip Upscayl image enhancement stage.
        no_translate: Skip Dutch translation stage.
        no_qrcode: Skip QR code generation for hyperlinks.
        no_makecode: Skip MakeCode screenshot replacement.
        no_download: Skip downloading and enhancing images (use existing files).

    Raises:
        SystemExit: On critical failures (unsupported URL, fetch error, extraction error,
            generation error, or save error). Non-critical failures (download, enhance,
            translate, makecode) log warnings and continue.
    """
    settings = get_settings()

    # Update logging level if verbose flag is used
    if verbose:
        setup_logging("DEBUG")

    extractor = ContentExtractor()
    output_dir = Path(output)

    # Check if we can handle this URL
    if not extractor.can_extract(url):
        console.print(f"[red]Error:[/red] No adapter available for URL: {url}")
        console.print("Supported sources: wiki.elecfreaks.com")
        raise SystemExit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        refresh_per_second=1,
        transient=True,
    ) as progress:
        # Fetch page
        task = progress.add_task("Fetching page...", total=None)
        try:
            html = await fetch_page(url)
            progress.update(task, description="Page fetched")
        except Exception as e:
            console.print(f"[red]Error fetching page:[/red] {e}")
            raise SystemExit(1)

        # Extract content
        progress.update(task, description="Extracting content...")
        try:
            content = extractor.extract(html, url)
        except Exception as e:
            console.print(f"[red]Error extracting content:[/red] {e}")
            raise SystemExit(1)

        # Create guide-specific subdirectory for assets
        filename = get_output_filename(url, content.title)
        guide_subdir = output_dir / filename

        # Replace MakeCode screenshots (optional)
        if not no_makecode and settings.MAKECODE_REPLACE_ENABLED:
            progress.update(task, description="Replacing MakeCode screenshots...")
            try:
                async with get_browser() as browser:
                    content = await replace_makecode_screenshots(
                        content, guide_subdir, browser, settings.MAKECODE_LANGUAGE
                    )
                replaced = content.metadata.get("makecode_replacements", 0)
                if replaced > 0:
                    progress.update(
                        task, description=f"Replaced {replaced} MakeCode screenshot(s)"
                    )
            except Exception as e:
                console.print(f"[yellow]Warning:[/yellow] MakeCode replacement failed: {e}")
                # Continue with original images

        # Handle images (download or use existing)
        if no_download:
            # Use existing downloaded/enhanced images
            progress.update(task, description="Using existing images...")
            content = use_existing_images(content, guide_subdir)
            found = sum(1 for img in content.images if img.get("local_path") or img.get("enhanced_path"))
            progress.update(task, description=f"Found {found}/{len(content.images)} existing images")
        else:
            # Download images
            progress.update(task, description="Downloading images...")
            try:
                content = await download_images(content, guide_subdir)
                downloaded = sum(1 for img in content.images if img.get("local_path"))
                progress.update(
                    task, description=f"Downloaded {downloaded}/{len(content.images)} images"
                )
            except Exception as e:
                console.print(f"[yellow]Warning:[/yellow] Image download failed: {e}")
                # Continue without images

            # Enhance images (optional)
            images_to_enhance = [
                img for img in content.images
                if img.get("local_path") and not img.get("replaced_with_dutch")
            ]
            if not no_enhance and images_to_enhance:
                progress.update(task, description="Enhancing images...")
                try:
                    content = enhance_all_images(
                        content, guide_subdir, show_progress=True
                    )
                    enhanced = sum(1 for img in content.images if img.get("enhanced_path"))
                    progress.update(
                        task,
                        description=f"Enhanced {enhanced}/{len(images_to_enhance)} images",
                    )
                except Exception as e:
                    console.print(f"[yellow]Warning:[/yellow] Image enhancement failed: {e}")
                    # Continue without enhancement

        # Translate content (optional)
        if not no_translate:
            progress.update(task, description="Translating to Dutch...")
            try:
                content = translate_content(content)
                progress.update(task, description="Translation complete")
            except Exception as e:
                console.print(f"[yellow]Warning:[/yellow] Translation failed: {e}")
                # Continue with English content

        # Generate markdown
        progress.update(task, description="Generating guide...")
        try:
            guide = generate_guide(content, output_dir=guide_subdir, add_qrcodes=not no_qrcode)
        except Exception as e:
            console.print(f"[red]Error generating guide:[/red] {e}")
            raise SystemExit(1)

        # Count QR codes if generated
        qr_count = guide.count("/qrcodes/") if not no_qrcode else 0
        if qr_count:
            progress.update(task, description=f"Generated {qr_count} QR codes")

        # Rename to project-based name if case number found
        case_number = extract_case_number(url)
        if case_number and content.title:
            new_filename = get_project_filename(case_number, content.title)
            guide_subdir, guide = rename_guide_directory(
                guide_subdir, new_filename, output_dir, guide
            )
            filename = new_filename

        # Save to file at root output directory
        progress.update(task, description="Saving guide...")
        output_path = output_dir / f"{filename}.md"

        try:
            save_guide(guide, output_path)
        except Exception as e:
            console.print(f"[red]Error saving guide:[/red] {e}")
            raise SystemExit(1)

    # Build success message
    downloaded = sum(1 for img in content.images if img.get("local_path"))
    enhanced = sum(1 for img in content.images if img.get("enhanced_path"))
    language = content.metadata.get("language", "en")

    # Encode title for safe console output
    safe_title = content.title.encode("ascii", errors="replace").decode("ascii")

    # Build message components
    message_parts = [
        "[green]Guide generated successfully![/green]\n\n",
        f"[bold]Title:[/bold] {safe_title}\n",
        f"[bold]Sections:[/bold] {len(content.sections)}\n",
        f"[bold]Images:[/bold] {downloaded} downloaded",
    ]

    if enhanced:
        message_parts.append(f", {enhanced} enhanced")

    message_parts.append(f"\n[bold]Language:[/bold] {language}")

    if qr_count > 0:
        message_parts.append(f"\n[bold]QR Codes:[/bold] {qr_count} generated")

    message_parts.append(f"\n[bold]Output:[/bold] {output_path}")

    console.print(
        Panel(
            "".join(message_parts),
            title="Success",
            border_style="green",
        )
    )

class BatchState:
    """Manages batch processing state for resume capability."""

    STATE_FILENAME = ".batch_state.json"

    def __init__(self, output_dir: Path) -> None:
        """Initialize batch state manager.

        Args:
            output_dir: Output directory where state file is stored.
        """
        self.output_dir = output_dir
        # Always store batch state in the config's output directory, not the user-specified one
        settings = get_settings()
        self.state_path = settings.output_path / self.STATE_FILENAME
        self.completed: set[str] = set()
        self.failed: set[str] = set()
        self.index_url: str = ""

    def load(self) -> bool:
        """Load state from file.

        Returns:
            True if state was loaded successfully.
        """
        if not self.state_path.exists():
            return False

        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            self.completed = set(data.get("completed", []))
            self.failed = set(data.get("failed", []))
            self.index_url = data.get("index_url", "")
            return True
        except (json.JSONDecodeError, IOError):
            return False

    def save(self) -> None:
        """Save state to file."""
        # Ensure parent directory of state file exists
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "index_url": self.index_url,
            "completed": list(self.completed),
            "failed": list(self.failed),
        }
        self.state_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def mark_completed(self, url: str) -> None:
        """Mark a tutorial as completed."""
        self.completed.add(url)
        self.failed.discard(url)
        self.save()

    def mark_failed(self, url: str) -> None:
        """Mark a tutorial as failed."""
        self.failed.add(url)
        self.save()

    def is_completed(self, url: str) -> bool:
        """Check if a tutorial has been completed."""
        return url in self.completed

    def clear(self) -> None:
        """Clear the state file."""
        if self.state_path.exists():
            self.state_path.unlink()
        self.completed.clear()
        self.failed.clear()
        self.index_url = ""


async def _generate_single(
    url: str,
    output_dir: Path,
    extractor: ContentExtractor,
    no_enhance: bool,
    no_translate: bool,
    no_qrcode: bool,
    no_makecode: bool,
    no_download: bool,
    progress: "Progress | None" = None,
) -> tuple[bool, str]:
    """Generate a single guide without console output (for batch processing).

    Args:
        url: Tutorial URL to process.
        output_dir: Output directory path.
        extractor: ContentExtractor instance.
        no_enhance: Skip image enhancement.
        no_translate: Skip Dutch translation.
        no_qrcode: Skip QR code generation.
        no_makecode: Skip MakeCode replacement.
        no_download: Skip downloading/enhancing images (use existing files).
        progress: Optional shared Progress instance for nested progress display.

    Returns:
        Tuple of (success, error_message).
    """
    settings = get_settings()

    try:
        # Fetch page
        html = await fetch_page(url)

        # Extract content
        content = extractor.extract(html, url)

        # Create guide-specific subdirectory
        filename = get_output_filename(url, content.title)
        guide_subdir = output_dir / filename

        # Replace MakeCode screenshots (optional)
        if not no_makecode and settings.MAKECODE_REPLACE_ENABLED:
            try:
                async with get_browser() as browser:
                    content = await replace_makecode_screenshots(
                        content, guide_subdir, browser, settings.MAKECODE_LANGUAGE
                    )
            except Exception:
                pass  # Continue with original images

        # Handle images (download or use existing)
        if no_download:
            # Use existing downloaded/enhanced images
            content = use_existing_images(content, guide_subdir)
        else:
            # Download images
            try:
                content = await download_images(content, guide_subdir)
            except Exception:
                pass  # Continue without images

            # Enhance images (optional)
            if not no_enhance and any(img.get("local_path") for img in content.images):
                try:
                    content = enhance_all_images(content, guide_subdir, progress=progress)
                except Exception:
                    pass  # Continue without enhancement

        # Translate content (optional)
        if not no_translate:
            try:
                content = translate_content(content)
            except Exception:
                pass  # Continue with English content

        # Generate markdown
        guide = generate_guide(content, output_dir=guide_subdir, add_qrcodes=not no_qrcode)

        # Rename to project-based name if case number found
        case_number = extract_case_number(url)
        if case_number and content.title:
            new_filename = get_project_filename(case_number, content.title)
            guide_subdir, guide = rename_guide_directory(
                guide_subdir, new_filename, output_dir, guide
            )
            filename = new_filename

        # Save to file
        output_path = output_dir / f"{filename}.md"
        save_guide(guide, output_path)

        return True, ""

    except Exception as e:
        return False, str(e)


async def _batch(
    index: str,
    output: str,
    verbose: bool,
    list_only: bool,
    resume: bool,
    no_enhance: bool,
    no_translate: bool,
    no_qrcode: bool,
    no_makecode: bool,
    no_download: bool,
) -> None:
    """Process all tutorials from an index page.

    Args:
        index: Index page URL containing tutorial links.
        output: Output directory path.
        verbose: Enable verbose logging.
        list_only: Only list tutorials without processing.
        resume: Resume from previous batch state.
        no_enhance: Skip image enhancement.
        no_translate: Skip Dutch translation.
        no_qrcode: Skip QR code generation.
        no_makecode: Skip MakeCode replacement.
        no_download: Skip downloading/enhancing images (use existing files).
    """
    settings = get_settings()

    # Update logging level if verbose flag is used
    if verbose:
        setup_logging("DEBUG")

    extractor = ContentExtractor()
    output_dir = Path(output)

    # Check if we can handle this URL
    if not extractor.can_extract(index):
        console.print(f"[red]Error:[/red] No adapter available for URL: {index}")
        console.print("Supported sources: wiki.elecfreaks.com")
        raise SystemExit(1)

    # Initialize batch state
    state = BatchState(output_dir)

    # Handle resume
    if resume:
        print(f"DEBUG: Looking for state file at: {state.state_path}")
        if state.load():
            print(f"DEBUG: State loaded successfully. Completed: {len(state.completed)}")
            if state.index_url and state.index_url != index:
                console.print(
                    f"[yellow]Warning:[/yellow] Index URL mismatch. "
                    f"Previous: {state.index_url}, Current: {index}"
                )
                console.print("Starting fresh batch...")
                state.clear()
            else:
                console.print(
                    f"[cyan]Resuming batch:[/cyan] {len(state.completed)} completed, "
                    f"{len(state.failed)} failed"
                )
        else:
            print("DEBUG: Failed to load state file")
            console.print("[yellow]No previous state found. Starting fresh batch...[/yellow]")

    # Fetch index page
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Fetching index page...", total=None)
        try:
            html = await fetch_page(index)
            progress.update(task, description="Index page fetched")
        except Exception as e:
            console.print(f"[red]Error fetching index page:[/red] {e}")
            raise SystemExit(1)

    # Extract tutorial links
    tutorials = extractor.extract_tutorial_links(html, index)

    if not tutorials:
        console.print("[yellow]No tutorials found on the index page.[/yellow]")
        raise SystemExit(0)

    # List only mode
    if list_only:
        table = Table(title=f"Tutorials Found ({len(tutorials)})")
        table.add_column("#", style="dim", width=4)
        table.add_column("Title", style="cyan")
        table.add_column("URL", style="dim", width=80, no_wrap=True)

        for i, tutorial in enumerate(tutorials, 1):
            # Encode title for safe console output
            safe_title = tutorial.title.encode("ascii", errors="replace").decode("ascii")
            table.add_row(str(i), safe_title, tutorial.url)

        console.print(table)
        return

    # Store index URL for resume
    state.index_url = index
    state.save()

    # Filter out completed tutorials if resuming
    pending_tutorials = [t for t in tutorials if not state.is_completed(t.url)]

    if not pending_tutorials:
        console.print("[green]All tutorials already processed![/green]")
        return

    console.print(
        f"[cyan]Processing {len(pending_tutorials)} tutorials "
        f"({len(tutorials) - len(pending_tutorials)} already completed)[/cyan]\n"
    )

    # Process tutorials with progress bar
    success_count = 0
    fail_count = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        main_task = progress.add_task(
            "Processing tutorials...", total=len(pending_tutorials)
        )

        for i, tutorial in enumerate(pending_tutorials, 1):
            # Update progress description
            safe_title = tutorial.title[:40] + "..." if len(tutorial.title) > 40 else tutorial.title
            progress.update(
                main_task,
                description=f"[{i}/{len(pending_tutorials)}] {safe_title}",
            )

            # Process tutorial
            success, error = await _generate_single(
                tutorial.url,
                output_dir,
                extractor,
                no_enhance,
                no_translate,
                no_qrcode,
                no_makecode,
                no_download,
                progress=progress,
            )

            if success:
                state.mark_completed(tutorial.url)
                success_count += 1
            else:
                state.mark_failed(tutorial.url)
                fail_count += 1
                if verbose:
                    console.print(f"[red]Failed:[/red] {tutorial.title}: {error}")

            progress.advance(main_task)

            # Rate limiting between tutorials
            if i < len(pending_tutorials):
                await asyncio.sleep(settings.RATE_LIMIT_SECONDS)

    # Summary
    console.print()
    summary_parts = [
        "[green]Batch processing complete![/green]\n\n",
        f"[bold]Total tutorials:[/bold] {len(tutorials)}\n",
        f"[bold]Processed:[/bold] {success_count + fail_count}\n",
        f"[bold]Successful:[/bold] {success_count}\n",
    ]

    if fail_count > 0:
        summary_parts.append(f"[bold]Failed:[/bold] [red]{fail_count}[/red]\n")

    if state.completed:
        summary_parts.append(f"[bold]Output:[/bold] {output_dir}")

    console.print(
        Panel(
            "".join(summary_parts),
            title="Batch Summary",
            border_style="green" if fail_count == 0 else "yellow",
        )
    )

    # Clean up state file on complete success
    if fail_count == 0:
        state.clear()


@click.group()
@click.version_option(version="0.1.0", prog_name="coderdojo")
def cli() -> None:
    """CoderDojo Guide Generator - Create printable guides from online tutorials."""
    # Initialize logging at startup
    setup_logging()

@cli.command()
@click.option("--url", required=True, help="Tutorial page URL")
@click.option("--output", "-o", default=None, help="Output directory (default: from OUTPUT_ROOT_DIR config)")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--no-enhance", is_flag=True, default=False, help="Skip image enhancement")
@click.option("--no-translate", is_flag=True, default=False, help="Skip Dutch translation")
@click.option("--no-qrcode", is_flag=True, default=False, help="Skip QR code generation for hyperlinks")
@click.option("--no-makecode", is_flag=True, default=False, help="Skip MakeCode screenshot replacement")
@click.option("--no-download", is_flag=True, default=False, help="Skip downloading/enhancing images (use existing files)")
def generate(url: str, output: str | None, verbose: bool, no_enhance: bool, no_translate: bool, no_qrcode: bool, no_makecode: bool, no_download: bool) -> None:
    """Generate a guide from a single tutorial URL.

    Downloads the tutorial page, extracts content, replaces MakeCode screenshots with
    Dutch versions, downloads and optionally enhances images, translates to Dutch,
    and saves as a Markdown file with local images.

    Output structure:
        <output>/
            <guide-name>.md              # Dutch Markdown guide
            <guide-name>/
                images/                  # Downloaded (and enhanced) images
                qrcodes/                 # QR codes for hyperlinks (unless --no-qrcode)
    """
    # Use settings default if output not specified
    if output is None:
        output = str(get_settings().output_path)
    asyncio.run(_generate(url, output, verbose, no_enhance, no_translate, no_qrcode, no_makecode, no_download))

@cli.command()
@click.option("--index", required=True, help="Index page URL containing tutorial links")
@click.option("--output", "-o", default=None, help="Output directory (default: from OUTPUT_ROOT_DIR config)")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--list-only", is_flag=True, help="List tutorials without processing")
@click.option("--resume", is_flag=True, help="Resume from previous batch state")
@click.option("--no-enhance", is_flag=True, default=False, help="Skip image enhancement")
@click.option("--no-translate", is_flag=True, default=False, help="Skip Dutch translation")
@click.option("--no-qrcode", is_flag=True, default=False, help="Skip QR code generation")
@click.option("--no-makecode", is_flag=True, default=False, help="Skip MakeCode screenshot replacement")
@click.option("--no-download", is_flag=True, default=False, help="Skip downloading/enhancing images (use existing files)")
def batch(
    index: str,
    output: str | None,
    verbose: bool,
    list_only: bool,
    resume: bool,
    no_enhance: bool,
    no_translate: bool,
    no_qrcode: bool,
    no_makecode: bool,
    no_download: bool,
) -> None:
    """Generate guides from all tutorials on an index page.

    Fetches the index page, extracts all tutorial links, and processes each
    tutorial through the full pipeline. Supports resuming interrupted batches.

    Example usage:
        uv run python -m src.cli batch --index "https://wiki.elecfreaks.com/en/microbit/building-blocks/nezha-inventors-kit/"
        uv run python -m src.cli batch --index "<URL>" --list-only
        uv run python -m src.cli batch --index "<URL>" --resume

    Output structure:
        <output>/
            <guide-1>.md
            <guide-1>/images/
            <guide-2>.md
            <guide-2>/images/
            ...
    """
    # Use settings default if output not specified
    if output is None:
        output = str(get_settings().output_path)
    asyncio.run(
        _batch(
            index,
            output,
            verbose,
            list_only,
            resume,
            no_enhance,
            no_translate,
            no_qrcode,
            no_makecode,
            no_download,
        )
    )


@cli.command()
def sources() -> None:
    """List supported source websites."""
    console.print(
        Panel(
            "[bold]Supported Sources:[/bold]\n\n"
            "- [cyan]wiki.elecfreaks.com[/cyan] - Elecfreaks Wiki\n"
            "  Nezha Inventor's Kit tutorials",
            title="Sources",
            border_style="blue",
        )
    )

@cli.command("print")
@click.option("--input", "-i", required=True, type=click.Path(exists=True, path_type=Path), help="Markdown file to convert to PDF")
@click.option("--output","-o",type=click.Path(path_type=Path),help="Output PDF path (defaults to same name with .pdf extension)",)
@click.option("--css",type=click.Path(exists=True, path_type=Path),help="Custom CSS file for styling (optional)",)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
def print_guide(input: Path, output: Path | None, css: Path | None, verbose: bool) -> None:
    """Convert a markdown guide to printable PDF.

    Generates a PDF with A4 portrait layout optimized for printing.
    Automatically detects and optimizes layout for different content types:
    - Construction diagrams: 2 per page
    - Connection diagrams: full page
    - Code screenshots: optimized size

    Example usage:
        uv run python -m src.cli print --input output/case-01.md
        uv run python -m src.cli print -i output/case-01.md -o guides/case-01.pdf
        uv run python -m src.cli print -i output/case-01.md --css custom.css

    """
    from src.printer import markdown_file_to_pdf

    # Update logging level if verbose flag is used
    if verbose:
        setup_logging("DEBUG")

    # Use default CSS if not provided
    if css is None:
        css = Path(__file__).parent.parent / "resources" / "print.css"
        if not css.exists():
            css = None  # Fall back to embedded CSS

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Converting to PDF...", total=None)

        try:
            pdf_path = markdown_file_to_pdf(input, output, css)
            progress.update(task, description="PDF generated")
        except Exception as e:
            console.print(f"[red]Error generating PDF:[/red] {e}")
            raise SystemExit(1)

    # Success message
    console.print(
        Panel(
            f"[green]PDF generated successfully![/green]\n\n"
            f"[bold]Input:[/bold] {input}\n"
            f"[bold]Output:[/bold] {pdf_path}",
            title="Success",
            border_style="green",
        )
    )

@cli.command("print-all")
@click.option("--input", "-i", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path), help="Directory containing markdown files to convert")
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Output directory for PDF files (defaults to same as input directory)")
@click.option("--css", type=click.Path(exists=True, path_type=Path), help="Custom CSS file for styling (optional)")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
def print_all(input: Path, output: Path | None, css: Path | None, verbose: bool) -> None:
    """Convert all markdown files in a directory to printable PDFs.

    Processes all .md files in the specified directory and converts them to PDF
    with the same filename but .pdf extension. Each file is processed individually
    with progress tracking.

    Example usage:
        uv run python -m src.cli print-all --input ./guides
        uv run python -m src.cli print-all -i ./guides -o ./pdfs
        uv run python -m src.cli print-all --input ./guides --css custom.css

    """
    from src.printer import markdown_file_to_pdf

    # Update logging level if verbose flag is used
    if verbose:
        setup_logging("DEBUG")

    # Use default CSS if not provided
    if css is None:
        css = Path(__file__).parent.parent / "resources" / "print.css"
        if not css.exists():
            css = None  # Fall back to embedded CSS

    # Set output directory
    if output is None:
        output = input

    # Find all markdown files
    md_files = list(input.glob("*.md"))

    if not md_files:
        console.print(f"[yellow]No markdown files found in {input}[/yellow]")
        return

    console.print(f"[cyan]Found {len(md_files)} markdown files to convert[/cyan]")

    # Process each file with progress bar
    success_count = 0
    error_count = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Converting files...", total=len(md_files))

        for i, md_file in enumerate(md_files, 1):
            # Update progress description
            progress.update(task, description=f"[{i}/{len(md_files)}] {md_file.name}")

            try:
                # Convert to PDF
                pdf_path = markdown_file_to_pdf(md_file, None, css)

                # Move to output directory if different
                if output != input:
                    target_pdf_path = output / pdf_path.name
                    pdf_path.rename(target_pdf_path)
                    pdf_path = target_pdf_path

                success_count += 1

            except Exception as e:
                error_count += 1
                if verbose:
                    console.print(f"[red]Failed to convert {md_file.name}:[/red] {e}")

            progress.advance(task)

    # Summary
    console.print()
    summary_parts = [
        "[green]Batch PDF conversion complete![/green]\n\n",
        f"[bold]Total files:[/bold] {len(md_files)}\n",
        f"[bold]Successful:[/bold] {success_count}\n",
    ]

    if error_count > 0:
        summary_parts.append(f"[bold]Failed:[/bold] [red]{error_count}[/red]\n")

    summary_parts.append(f"[bold]Output directory:[/bold] {output}")

    console.print(
        Panel(
            "".join(summary_parts),
            title="Batch Summary",
            border_style="green" if error_count == 0 else "yellow",
        )
    )

@cli.command()
@click.option(
    "--input", "-i",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Directory containing markdown guide files"
)
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    help="Output path for catalog file (defaults to <input>/catalog.md)"
)
@click.option(
    "--title", "-t",
    default="Project Catalogus",
    help="Title for the catalog document"
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
def catalog(input: Path, output: Path | None, title: str, verbose: bool) -> None:
    """Generate a catalog document from all project guides.

    Creates a markdown document containing a table of contents and summary
    entries for each project guide found in the input directory. Each entry
    includes the project title, introduction, main image, and a link to the
    full guide.

    The catalog is designed for printing, with page breaks between projects.

    Example usage:
        uv run python -m src.cli catalog --input ./output
        uv run python -m src.cli catalog -i ./output -o ./output/my-catalog.md
        uv run python -m src.cli catalog -i ./output --title "Nezha Kit Projects"

    Output structure:
        The catalog includes:
        - Table of contents with links to each project
        - Project entries with title, image, introduction, and guide link
        - Page breaks between projects for PDF printing
    """
    # Update logging level if verbose flag is used
    if verbose:
        setup_logging("DEBUG")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Generating catalog...", total=None)

        try:
            catalog_path = generate_catalog(input, output, title)
            progress.update(task, description="Catalog generated")
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise SystemExit(1)
        except Exception as e:
            console.print(f"[red]Error generating catalog:[/red] {e}")
            raise SystemExit(1)

    # Count guides included
    md_count = len([f for f in input.glob("*.md") if f.name != "catalog.md"])

    # Success message
    console.print(
        Panel(
            f"[green]Catalog generated successfully![/green]\n\n"
            f"[bold]Title:[/bold] {title}\n"
            f"[bold]Guides included:[/bold] {md_count}\n"
            f"[bold]Output:[/bold] {catalog_path}",
            title="Success",
            border_style="green",
        )
    )


if __name__ == "__main__":
    import sys
    
    # Check if command line parameters are provided
    if len(sys.argv) > 1:
        # Run CLI mode with parameters
        cli()
    else:
        # Run hardcoded test mode
        print("No parameters provided, running hardcoded test...")
        
        # Hardcoded test parameters
        url = "https://wiki.elecfreaks.com/en/microbit/building-blocks/nezha-inventors-kit/Nezha_Inventor_s_kit_for_microbit_case_75"
        output_dir = "D:/Coderdojo/Projects"  # Renamed to avoid conflict with function parameter
        verbose = True
        no_enhance = False
        no_translate = False
        no_qrcode = False
        no_makecode = False
        no_download = False

        print(f"Generating guide from: {url}")
        print(f"Output directory: {output_dir}")
        print(f"Options: verbose={verbose}, no_enhance={no_enhance}, no_translate={no_translate}")
        print(f"Options: no_qrcode={no_qrcode}, no_makecode={no_makecode}, no_download={no_download}")

        # Run the generation
        asyncio.run(_generate(url, output_dir, verbose, no_enhance, no_translate, no_qrcode, no_makecode, no_download))