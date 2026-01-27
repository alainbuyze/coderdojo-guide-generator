"""Image enhancement using Upscayl CLI."""

import inspect
import logging
import shutil
import subprocess
import sys
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

# Handle imports for both module and standalone execution
try:
    from src.core.config import get_settings
    from src.image_trimmer import trim_image
    from src.sources.base import ExtractedContent
except ImportError:
    # Running as standalone script
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.core.config import get_settings
    from src.image_trimmer import trim_image
    from src.sources.base import ExtractedContent

settings = get_settings()
logger = logging.getLogger(__name__)
console = Console()

# Minimum file size to enhance (skip tiny images)
MIN_FILE_SIZE_BYTES = 10 * 1024  # 10KB


def find_upscayl_binary() -> Path | None:
    """Find the Upscayl binary.

    Returns:
        Path to binary if found, None otherwise.
    """
    # Check configured path first
    configured_path = Path(settings.UPSCAYL_PATH)
    if configured_path.exists():
        return configured_path

    # Check common Windows locations
    common_paths = [
        Path("C:/Program Files/Upscayl/resources/bin/upscayl-bin.exe"),
        Path("C:/Program Files (x86)/Upscayl/resources/bin/upscayl-bin.exe"),
    ]

    for path in common_paths:
        if path.exists():
            return path

    # Check if in PATH
    which_result = shutil.which("upscayl-bin")
    if which_result:
        return Path(which_result)

    return None


def enhance_image(input_path: Path, output_path: Path) -> bool:
    """Enhance a single image using Upscayl.

    Args:
        input_path: Path to input image.
        output_path: Path to save enhanced image.

    Returns:
        True if enhancement succeeded, False otherwise.
    """
    logger.debug(f" * {inspect.currentframe().f_code.co_name} > Enhancing: {input_path}")

    # Check file size
    if input_path.stat().st_size < MIN_FILE_SIZE_BYTES:
        logger.debug(f"    -> Skipping (too small): {input_path.stat().st_size} bytes")
        return False

    # Find Upscayl binary
    upscayl_bin = find_upscayl_binary()
    if not upscayl_bin:
        logger.warning("    -> Upscayl binary not found, skipping enhancement")
        return False

    # Check if models directory exists
    models_dir = upscayl_bin.parent.parent / "models"  # Go from bin to resources, then to models
    if not models_dir.exists():
        logger.warning(f"    -> Models directory not found: {models_dir}")
        return False

    # Check if specific model file exists
    model_file = models_dir / f"{settings.UPSCAYL_MODEL}.param"
    if not model_file.exists():
        logger.warning(f"    -> Model file not found: {model_file}")
        available_models = list(models_dir.glob("*.param")) if models_dir.exists() else []
        if available_models:
            logger.debug(f"    -> Available models: {[m.stem for m in available_models]}")
        return False

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build command
    upscayl_dir = upscayl_bin.parent  # resources/bin directory
    resources_dir = upscayl_dir.parent  # resources directory

    # Use absolute paths to avoid working directory issues
    input_abs = input_path.resolve()
    output_abs = output_path.resolve()

    cmd = [
        str(upscayl_bin),
        "-i",
        str(input_abs),
        "-o",
        str(output_abs),
        "-z",  # Scale parameter (not -s)
        str(settings.UPSCAYL_SCALE),
        "-n",
        settings.UPSCAYL_MODEL,
        "-g",
        settings.UPSCAYL_GPU_ID,
        "-j",
        settings.UPSCAYL_THREADS,
    ]

    try:
        # Run without text capture first to avoid encoding issues
        result = subprocess.run(
            cmd,
            cwd=str(resources_dir),  # Set working directory to resources directory
            capture_output=True,
            timeout=settings.ENHANCE_TIMEOUT,
        )

        # Decode stderr carefully for error messages
        stderr_text = ""
        if result.stderr:
            try:
                stderr_text = result.stderr.decode('utf-8', errors='replace')
            except UnicodeDecodeError:
                stderr_text = result.stderr.decode('latin1', errors='replace')

        # Decode stdout if needed for debugging
        stdout_text = ""
        if result.stdout:
            try:
                stdout_text = result.stdout.decode('utf-8', errors='replace')
            except UnicodeDecodeError:
                stdout_text = result.stdout.decode('latin1', errors='replace')

        if result.returncode != 0:
            logger.warning(f"    -> Enhancement failed for {input_path.name}")
            logger.debug(f" Error: {stderr_text}")
            logger.debug(f"    -> Command: {' '.join(cmd)}")
            logger.debug(f"    -> Working directory: {resources_dir}")
            logger.debug(f"    -> stdout: {stdout_text}")
            logger.debug(f"    -> stderr: {stderr_text}")
            logger.debug(f"    -> Return code: {result.returncode}")
            return False

        if output_path.exists():
            #logger.debug(f"    -> Enhanced: {output_path}")
            return True
        else:
            logger.warning(f"    -> Output file not created for {input_path.name}")
            logger.debug(f"    -> Expected output at: {output_path}")
            logger.debug(f"    -> Output parent exists: {output_path.parent.exists()}")
            logger.debug(f"    -> Output parent writable: {oct(output_path.parent.stat().st_mode)[-3:]}")
            return False

    except subprocess.TimeoutExpired:
        logger.warning(f"    -> Enhancement timed out for: {input_path}")
        return False
    except Exception as e:
        logger.error(f"    -> Enhancement error for {input_path}: {e}")
        return False


def _process_single_image(
    image: dict, base_dir: Path
) -> tuple[dict, str | None, bool]:
    """Process a single image for enhancement.

    Args:
        image: Image dictionary with local_path.
        base_dir: Base directory for resolving paths.

    Returns:
        Tuple of (image dict, enhanced_path or None, success bool).
    """
    local_path = image["local_path"]
    input_path = base_dir / local_path

    if not input_path.exists():
        logger.warning(f"    -> Local image not found: {input_path}")
        return image, None, False

    # Skip GIF files (animated images)
    if input_path.suffix.lower() == '.gif':
        logger.debug(f"    -> Skipping GIF file: {input_path.name}")
        return image, None, False

    # Generate enhanced path (add _enhanced before extension)
    stem = input_path.stem
    suffix = input_path.suffix
    enhanced_filename = f"{stem}_enhanced{suffix}"
    enhanced_path = input_path.parent / enhanced_filename

    # Enhance
    success = enhance_image(input_path, enhanced_path)

    if success:
        # Trim the enhanced image to remove whitespace
        try:
            trim_image(enhanced_path)
            logger.debug(f"    -> Trimmed: {enhanced_path.name}")
        except Exception as e:
            logger.warning(f"    -> Failed to trim {enhanced_path.name}: {e}")

        # Remove the original image
        try:
            input_path.unlink()
            logger.debug(f"    -> Removed original: {input_path.name}")
        except Exception as e:
            logger.warning(f"    -> Failed to remove original {input_path.name}: {e}")

        # Return relative path for markdown
        relative_enhanced = Path(local_path).parent / enhanced_filename
        return image, str(relative_enhanced), True
    else:
        # Fall back to original - no enhanced_path set
        logger.debug(f"    -> Keeping original for: {local_path}")
        return image, None, False


def enhance_all_images(
    content: ExtractedContent,
    output_dir: Path,
    progress_callback: Callable[[int, int], None] | None = None,
    show_progress: bool = False,
    progress: Progress | None = None,
) -> ExtractedContent:
    """Enhance all downloaded images in content using parallel processing.

    Processes images that have local_path set by the downloader.
    Enhanced images are saved with '_enhanced' suffix.

    Args:
        content: Extracted content with downloaded images.
        output_dir: Base output directory.
        progress_callback: Optional callback(completed, total) for progress updates.
        show_progress: Show rich progress bar (used when running standalone).
        progress: Optional shared Progress instance for nested progress display.

    Returns:
        Updated ExtractedContent with enhanced_path set for enhanced images.

    Raises:
        EnhancementError: If critical enhancement failure occurs.
    """
    logger.debug(f" * {inspect.currentframe().f_code.co_name} > Enhancing images in {output_dir}")

    # Check if enhancement is enabled
    if not settings.ENHANCE_IMAGES:
        logger.debug("    -> Enhancement disabled in settings")
        return content

    # Check for Upscayl
    upscayl_bin = find_upscayl_binary()
    if not upscayl_bin:
        logger.warning("    -> Upscayl not found, skipping all enhancements")
        return content

    # Find images with local paths (skip MakeCode-replaced images - they're already high quality)
    images_to_enhance = [
        img for img in content.images
        if img.get("local_path") and not img.get("replaced_with_dutch")
    ]

    if not images_to_enhance:
        logger.debug("    -> No local images to enhance")
        return content

    num_workers = settings.ENHANCE_WORKERS
    logger.debug(f"    -> Found {len(images_to_enhance)} images to enhance (using {num_workers} workers)")

    enhanced_count = 0
    # Use parent directory since local_path includes guide subfolder name
    base_dir = output_dir.parent
    total_count = len(images_to_enhance)

    def _process_with_progress(progress: Progress | None, task_id: int | None) -> int:
        """Process all images and return enhanced count."""
        nonlocal enhanced_count
        processed_count = 0

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            # Submit all enhancement tasks
            future_to_image = {
                executor.submit(_process_single_image, image, base_dir): image
                for image in images_to_enhance
            }

            # Collect results as they complete
            for future in as_completed(future_to_image):
                try:
                    image, enhanced_path, success = future.result()
                    if success and enhanced_path:
                        image["enhanced_path"] = enhanced_path
                        enhanced_count += 1
                except Exception as e:
                    original_image = future_to_image[future]
                    logger.error(f"    -> Enhancement failed for {original_image.get('local_path')}: {e}")

                processed_count += 1

                # Update progress
                if progress and task_id is not None:
                    progress.update(task_id, completed=processed_count)
                if progress_callback:
                    progress_callback(processed_count, total_count)

        return enhanced_count

    # Show rich progress bar if requested
    if progress is not None:
        # Use shared progress instance (add a separate task for image enhancement)
        task_id = progress.add_task("  Enhancing images...", total=total_count)
        enhanced_count = _process_with_progress(progress, task_id)
        progress.update(task_id, description=f"  Enhanced {enhanced_count}/{total_count} images")
        progress.remove_task(task_id)
    elif show_progress:
        # Create own progress instance when running standalone
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            refresh_per_second=1,
            console=console,
        ) as standalone_progress:
            task_id = standalone_progress.add_task("Enhancing images...", total=total_count)
            enhanced_count = _process_with_progress(standalone_progress, task_id)
            standalone_progress.update(task_id, description=f"Enhanced {enhanced_count}/{total_count} images")
    else:
        _process_with_progress(None, None)

    logger.debug(f"    -> Enhanced {enhanced_count}/{len(images_to_enhance)} images")
    return content


if __name__ == "__main__":
    """Test the enhancer with a single file."""
    import argparse
    import sys
    from pathlib import Path

    from rich.panel import Panel

    parser = argparse.ArgumentParser(description="Test image enhancement with Upscayl")
    parser.add_argument("input", help="Input image path")
    parser.add_argument("output", help="Output image path")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # Set up logging
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
    else:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # Validate input file
    input_path = Path(args.input)
    if not input_path.exists():
        console.print(f"[red]Error:[/red] Input file not found: {input_path}")
        sys.exit(1)

    # Enhance the image with progress
    output_path = Path(args.output)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task(f"Enhancing {input_path.name}...", total=None)
        success = enhance_image(input_path, output_path)
        if success:
            progress.update(task, description="Enhancement complete")

    if success:
        console.print(
            Panel(
                f"[green]Enhancement successful![/green]\n\n"
                f"[bold]Input:[/bold] {input_path}\n"
                f"[bold]Output:[/bold] {output_path}\n"
                f"[bold]File size:[/bold] {output_path.stat().st_size:,} bytes",
                title="Success",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                f"[red]Enhancement failed[/red]\n\n"
                f"[bold]Input:[/bold] {input_path}\n"
                f"[bold]Output:[/bold] {output_path}",
                title="Error",
                border_style="red",
            )
        )
        sys.exit(1)
