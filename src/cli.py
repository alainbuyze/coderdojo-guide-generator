"""Command-line interface for the CoderDojo Guide Generator."""

import asyncio
import re
from pathlib import Path
from urllib.parse import urlparse

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.core.config import get_settings
from src.core.logging import setup_logging
from src.downloader import download_images
from src.enhancer import enhance_all_images
from src.extractor import ContentExtractor
from src.generator import generate_guide, save_guide
from src.makecode_replacer import replace_makecode_screenshots
from src.scraper import fetch_page, get_browser
from src.translator import translate_content

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


async def _generate(
    url: str, output: str, verbose: bool, no_enhance: bool, no_translate: bool, no_qrcode: bool, no_makecode: bool
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

    Raises:
        SystemExit: On critical failures (unsupported URL, fetch error, extraction error,
            generation error, or save error). Non-critical failures (download, enhance,
            translate, makecode) log warnings and continue.
    """
    settings = get_settings()

    # Setup logging
    log_level = "DEBUG" if verbose else settings.LOG_LEVEL
    setup_logging(log_level)

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
        console=console,
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

        # Replace MakeCode screenshots (optional)
        if not no_makecode and settings.MAKECODE_REPLACE_ENABLED:
            progress.update(task, description="Replacing MakeCode screenshots...")
            try:
                async with get_browser() as browser:
                    content = await replace_makecode_screenshots(
                        content, output_dir, browser, settings.MAKECODE_LANGUAGE
                    )
                replaced = content.metadata.get("makecode_replacements", 0)
                if replaced > 0:
                    progress.update(
                        task, description=f"Replaced {replaced} MakeCode screenshot(s)"
                    )
            except Exception as e:
                console.print(f"[yellow]Warning:[/yellow] MakeCode replacement failed: {e}")
                # Continue with original images

        # Download images
        progress.update(task, description="Downloading images...")
        try:
            content = await download_images(content, output_dir)
            downloaded = sum(1 for img in content.images if img.get("local_path"))
            progress.update(
                task, description=f"Downloaded {downloaded}/{len(content.images)} images"
            )
        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Image download failed: {e}")
            # Continue without images

        # Enhance images (optional)
        if not no_enhance and any(img.get("local_path") for img in content.images):
            progress.update(task, description="Enhancing images...")
            try:
                content = enhance_all_images(content, output_dir)
                enhanced = sum(1 for img in content.images if img.get("enhanced_path"))
                progress.update(task, description=f"Enhanced {enhanced} images")
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
            guide = generate_guide(content, output_dir=output_dir, add_qrcodes=not no_qrcode)
        except Exception as e:
            console.print(f"[red]Error generating guide:[/red] {e}")
            raise SystemExit(1)

        # Count QR codes if generated
        qr_count = guide.count("![](qrcodes/") if not no_qrcode else 0
        if qr_count:
            progress.update(task, description=f"Generated {qr_count} QR codes")

        # Save to file
        progress.update(task, description="Saving guide...")
        filename = get_output_filename(url, content.title)
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
        f"[green]Guide generated successfully![/green]\n\n",
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


@click.group()
@click.version_option(version="0.1.0", prog_name="coderdojo")
def cli() -> None:
    """CoderDojo Guide Generator - Create printable guides from online tutorials."""
    pass


@cli.command()
@click.option("--url", required=True, help="Tutorial page URL")
@click.option("--output", "-o", default="./output", help="Output directory")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--no-enhance", is_flag=True, help="Skip image enhancement")
@click.option("--no-translate", is_flag=True, help="Skip Dutch translation")
@click.option("--no-qrcode", is_flag=True, help="Skip QR code generation for hyperlinks")
@click.option("--no-makecode", is_flag=True, help="Skip MakeCode screenshot replacement")
def generate(url: str, output: str, verbose: bool, no_enhance: bool, no_translate: bool, no_makecode: bool, no_qrcode: bool) -> None:
    """Generate a guide from a single tutorial URL.

    Downloads the tutorial page, extracts content, replaces MakeCode screenshots with
    Dutch versions, downloads and optionally enhances images, translates to Dutch,
    and saves as a Markdown file with local images.

    Output structure:
        <output>/
            <guide-name>.md      # Dutch Markdown guide
            images/              # Downloaded (and enhanced) images
            qrcodes/             # QR codes for hyperlinks (unless --no-qrcode)
    """
    asyncio.run(_generate(url, output, verbose, no_enhance, no_translate, no_qrcode))
    asyncio.run(_generate(url, output, verbose, no_enhance, no_translate, no_makecode))


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


if __name__ == "__main__":
    cli()
