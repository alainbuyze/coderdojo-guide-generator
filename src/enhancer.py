"""Image enhancement using Upscayl CLI."""

import inspect
import logging
import shutil
import subprocess
import sys
from pathlib import Path

# Handle imports for both module and standalone execution
try:
    from src.core.config import get_settings
    from src.sources.base import ExtractedContent
except ImportError:
    # Running as standalone script
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.core.config import get_settings
    from src.sources.base import ExtractedContent

settings = get_settings()
logger = logging.getLogger(__name__)

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
    ]

    try:
        # Run without text capture first to avoid encoding issues
        result = subprocess.run(
            cmd,
            cwd=str(resources_dir),  # Set working directory to resources directory
            capture_output=True,
            timeout=120,  # 2 minute timeout per image
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
            logger.warning(f"    -> Enhancement failed: {stderr_text}")
            logger.debug(f"    -> Command: {' '.join(cmd)}")
            logger.debug(f"    -> Working directory: {resources_dir}")
            logger.debug(f"    -> stdout: {stdout_text}")
            logger.debug(f"    -> stderr: {stderr_text}")
            logger.debug(f"    -> Return code: {result.returncode}")
            return False

        if output_path.exists():
            logger.debug(f"    -> Enhanced: {output_path}")
            return True
        else:
            logger.warning("    -> Output file not created")
            logger.debug(f"    -> Expected output at: {output_path}")
            logger.debug(f"    -> Output parent exists: {output_path.parent.exists()}")
            logger.debug(f"    -> Output parent writable: {oct(output_path.parent.stat().st_mode)[-3:]}")
            return False

    except subprocess.TimeoutExpired:
        logger.warning(f"    -> Enhancement timed out for: {input_path}")
        return False
    except Exception as e:
        logger.error(f"    -> Enhancement error: {e}")
        return False


def enhance_all_images(content: ExtractedContent, output_dir: Path) -> ExtractedContent:
    """Enhance all downloaded images in content.

    Processes images that have local_path set by the downloader.
    Enhanced images are saved with '_enhanced' suffix.

    Args:
        content: Extracted content with downloaded images.
        output_dir: Base output directory.

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

    # Find images with local paths
    images_to_enhance = [img for img in content.images if img.get("local_path")]

    if not images_to_enhance:
        logger.debug("    -> No local images to enhance")
        return content

    logger.debug(f"    -> Found {len(images_to_enhance)} images to enhance")

    enhanced_count = 0
    for image in images_to_enhance:
        local_path = image["local_path"]
        input_path = output_dir / local_path

        if not input_path.exists():
            logger.warning(f"    -> Local image not found: {input_path}")
            continue

        # Generate enhanced path (add _enhanced before extension)
        stem = input_path.stem
        suffix = input_path.suffix
        enhanced_filename = f"{stem}_enhanced{suffix}"
        enhanced_path = input_path.parent / enhanced_filename

        # Enhance
        success = enhance_image(input_path, enhanced_path)

        if success:
            # Store relative path for markdown
            relative_enhanced = Path(local_path).parent / enhanced_filename
            image["enhanced_path"] = str(relative_enhanced)
            enhanced_count += 1
        else:
            # Fall back to original - no enhanced_path set
            logger.debug(f"    -> Keeping original for: {local_path}")

    logger.debug(f"    -> Enhanced {enhanced_count}/{len(images_to_enhance)} images")
    return content


if __name__ == "__main__":
    """Test the enhancer with a single file."""
    import argparse
    import sys
    from pathlib import Path

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
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)

    # Enhance the image
    output_path = Path(args.output)
    print(f"Enhancing {input_path} -> {output_path}")

    success = enhance_image(input_path, output_path)

    if success:
        print(f"✓ Enhancement successful: {output_path}")
        print(f"  File size: {output_path.stat().st_size} bytes")
    else:
        print("✗ Enhancement failed")
        sys.exit(1)
